"""Admin-side notifications for payment + promo events.

Sends Telegram messages to the admin chat when noteworthy events happen
(new deal initiated, promo applied, subscription activated, etc.).

All functions are called from view code wrapped in `try/except Exception: pass`
so failures here never affect the user-facing flow.
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _admin_chat_id():
    return getattr(settings, 'TELEGRAM_ADMIN_CHAT_ID', '') or getattr(settings, 'ADMIN_TELEGRAM_CHAT_ID', '')


def _bot_token():
    return getattr(settings, 'TELEGRAM_BOT_TOKEN', '')


def _send(text):
    chat = _admin_chat_id()
    token = _bot_token()
    if not chat or not token:
        return
    try:
        requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={'chat_id': chat, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': True},
            timeout=5,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning('admin_notify send failed: %s', exc)


def _user_label(user):
    parts = []
    if getattr(user, 'email', '') and not user.email.startswith('tg_'):
        parts.append(user.email)
    if getattr(user, 'telegram_username', ''):
        parts.append(f'@{user.telegram_username}')
    elif getattr(user, 'telegram_id', None):
        parts.append(f'tg:{user.telegram_id}')
    parts.append(f'#{user.id}')
    return ' / '.join(parts)


def notify_payment_initiated(user, subscription, amount, method, crypto_asset=None):
    """Called after a pending Subscription is created and the invoice is generated."""
    asset = f' ({crypto_asset})' if crypto_asset else ''
    text = (
        '💰 <b>New deal</b>\n'
        f'user: {_user_label(user)}\n'
        f'plan: <b>{subscription.plan}</b>, {subscription.period_months} мес\n'
        f'amount: {amount}₽ via {method}{asset}\n'
        f'sub_id: {subscription.id}'
    )
    _send(text)


def notify_payment_completed(user, subscription):
    text = (
        '✅ <b>Payment completed</b>\n'
        f'user: {_user_label(user)}\n'
        f'plan: <b>{subscription.plan}</b>, {subscription.period_months} мес\n'
        f'paid: {subscription.price_paid}₽\n'
        f'sub_id: {subscription.id}'
    )
    _send(text)


def notify_promo_applied(user, promo, context='purchase', bonus_days=0, discount_amount=0):
    extra = ''
    if context == 'gift':
        extra = f' (+{bonus_days} days)'
    elif discount_amount:
        extra = f' (-{discount_amount}₽)'
    text = (
        '🎟 <b>Promo applied</b>\n'
        f'user: {_user_label(user)}\n'
        f'code: <b>{promo.code}</b> [{promo.promo_type}]\n'
        f'context: {context}{extra}'
    )
    _send(text)
