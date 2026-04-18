"""Auto-renewal system for EIFAVPN subscriptions.

Generates proactive invoice links and sends them via Telegram
for users with auto_renew=True before their subscription expires.
"""

import logging
from datetime import timedelta

from django.utils import timezone

from accounts.models import User, Subscription
from .invoices import create_stars_invoice, create_crypto_invoice, create_wata_invoice
from .plans import PLANS, get_price
from .date_utils import add_months

logger = logging.getLogger(__name__)


def generate_renewal_invoice(user, current_sub):
    """Create a pending Subscription and generate an invoice link for renewal.

    Returns dict {payment_url, payment_id, subscription_id} or None on failure.
    """
    plan = current_sub.plan
    period = current_sub.period_months or 1
    method = user.preferred_payment_method or current_sub.payment_method

    if method not in ('stars', 'crypto', 'wata'):
        method = 'stars'  # default fallback

    if plan not in PLANS:
        return None

    price = get_price(plan, period)

    # Referral discount
    if user.referred_by:
        price = round(price * 0.90)

    price = max(price, 1)

    # Cancel any existing pending renewal subs
    Subscription.objects.filter(
        user=user, status='pending', payment_method__startswith='renewal_'
    ).update(status='cancelled')

    # Create pending subscription for renewal
    from datetime import datetime, timezone as tz
    sub = Subscription.objects.create(
        user=user,
        plan=plan,
        period_months=period,
        price_paid=price,
        payment_method=f'renewal_{method}',
        status='pending',
        expires_at=add_months(datetime.now(tz.utc), period),
    )

    # Generate invoice
    if method == 'stars':
        invoice = create_stars_invoice(sub, price)
    elif method == 'crypto':
        crypto_asset = user.preferred_crypto_asset or 'USDT'
        invoice = create_crypto_invoice(sub, price, crypto_asset)
    elif method == 'wata':
        invoice = create_wata_invoice(sub, price)
    else:
        invoice = {'error': 'Unknown method'}

    if invoice.get('error'):
        logger.warning(f'Renewal invoice failed for user {user.id}: {invoice["error"]}')
        sub.delete()
        return None

    sub.payment_id = invoice.get('payment_id', '')
    sub.save(update_fields=['payment_id'])

    return {
        'payment_url': invoice.get('payment_url'),
        'payment_id': invoice.get('payment_id'),
        'subscription_id': sub.id,
    }


def run_auto_renewal():
    """Cron function: find auto-renew users with expiring subs, generate invoices, notify.

    Called daily by management command.
    Returns stats dict.
    """
    from .notifications import notify_renewal_available

    now = timezone.now()
    today = now.date()
    stats = {'3day': 0, '1day': 0, 'same_day': 0, 'failed': 0}

    # Find users with auto_renew=True and active subscription
    users_with_auto = User.objects.filter(
        auto_renew=True,
        telegram_id__isnull=False,
    ).prefetch_related('subscriptions')

    for user in users_with_auto:
        active_sub = user.subscriptions.filter(
            status='paid', expires_at__gt=now
        ).order_by('-expires_at').first()

        if not active_sub:
            continue

        days_left = (active_sub.expires_at.date() - today).days

        if days_left == 3:
            # 3 days before: send deep link to purchase page (invoice would expire)
            from django.conf import settings
            app_url = getattr(settings, 'APP_URL', 'https://eifavpn.ru')
            payment_url = f'{app_url}/cabinet/purchase?renew=1'
            notify_renewal_available(user, 3, payment_url)
            stats['3day'] += 1

        elif days_left in (1, 0):
            # 1 day or same day: generate actual invoice link
            result = generate_renewal_invoice(user, active_sub)
            if result:
                notify_renewal_available(user, days_left, result['payment_url'])
                key = '1day' if days_left == 1 else 'same_day'
                stats[key] += 1
            else:
                stats['failed'] += 1

    logger.info(f'Auto-renewal run: {stats}')
    return stats
