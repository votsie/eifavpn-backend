import json
import hashlib
import hmac
import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from django.db.models import F
from accounts.models import Subscription, Referral, PromoCode, PromoCodeUsage
from .plans import PLANS, PRICING, get_price, get_price_with_referral, REFERRAL_BONUS_DAYS
from .promo_utils import validate_promo_for_user, calculate_promo_price
from .exchange_rates import get_rates, rub_to_crypto, rub_to_stars
from . import remnawave


class PlansView(APIView):
    """GET /api/subscriptions/plans/ — list available plans with prices."""
    permission_classes = [AllowAny]

    def get(self, request):
        plans = []
        for plan_id, config in PLANS.items():
            plans.append({
                'id': plan_id,
                'name': config['name'],
                'servers': config['servers'],
                'devices': config['devices'],
                'adblock': config['adblock'],
                'p2p': config['p2p'],
                'unlimited_traffic': config['traffic_bytes'] == 0,
                'pricing': PRICING[plan_id],
            })
        return Response(plans)


class ExchangeRatesView(APIView):
    """GET /api/subscriptions/rates/ — current crypto exchange rates."""
    permission_classes = [AllowAny]

    def get(self, request):
        rates = get_rates()
        # Also calculate example: 99 RUB in crypto
        amount = float(request.query_params.get('amount', 0))
        result = {
            'rates': {
                'USDT': rates.get('USDT', 0),
                'TON': rates.get('TON', 0),
                'BTC': rates.get('BTC', 0),
            },
            'source': rates.get('source', '?'),
            'markup': 1.03,
        }
        from .exchange_rates import get_star_price_rub
        result['star_price_rub'] = get_star_price_rub()

        if amount > 0:
            result['converted'] = {
                'USDT': rub_to_crypto(amount, 'USDT'),
                'TON': rub_to_crypto(amount, 'TON'),
                'stars': rub_to_stars(amount),
            }
        return Response(result)


class ValidatePromoView(APIView):
    """POST /api/subscriptions/validate-promo/ — validate a promo code."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get('code', '').strip()
        plan = request.data.get('plan')
        period = request.data.get('period')

        if not code:
            return Response({'valid': False, 'error': 'Введите промокод'})

        if period:
            period = int(period)

        promo, error = validate_promo_for_user(request.user, code, plan, period)
        if error:
            return Response({'valid': False, 'error': error})

        result = {
            'valid': True,
            'code': promo.code,
            'promo_type': promo.promo_type,
            'value': promo.value,
            'description': promo.description,
            'allowed_plans': [promo.plan] if promo.plan else [],
            'allowed_periods': promo.allowed_periods or [],
        }

        if plan and period and promo.promo_type != 'gift':
            has_referral = request.user.referred_by is not None
            price_info = calculate_promo_price(promo, plan, period, has_referral)
            result.update(price_info)

        return Response(result)


class ActivateGiftView(APIView):
    """POST /api/subscriptions/activate-gift/ — activate a gift promo (free days)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get('code', '').strip()
        if not code:
            return Response({'error': 'Введите промокод'}, status=400)

        promo, error = validate_promo_for_user(request.user, code)
        if error:
            return Response({'error': error}, status=400)

        if promo.promo_type != 'gift':
            return Response({'error': 'Этот промокод не является подарочным'}, status=400)

        user = request.user
        gift_plan = promo.plan or 'standard'
        gift_days = promo.value

        from datetime import datetime, timedelta, timezone as tz

        try:
            if user.remnawave_uuid:
                remnawave.extend_subscription(user.remnawave_uuid, gift_days)
            else:
                rmn_user = remnawave.create_subscription(user, gift_plan, days=gift_days)
                user.remnawave_uuid = rmn_user['uuid']
                user.remnawave_short_uuid = rmn_user['shortUuid']
                user.subscription_url = rmn_user.get('subscriptionUrl', '')
                user.save()
        except Exception as e:
            return Response({'error': f'Ошибка активации: {str(e)}'}, status=500)

        # Record usage
        PromoCodeUsage.objects.create(
            promo=promo, user=user, bonus_days=gift_days
        )
        PromoCode.objects.filter(pk=promo.pk).update(times_used=F('times_used') + 1)

        # Admin notification: promo applied
        try:
            from .admin_notify import notify_promo_applied
            notify_promo_applied(user, promo, context='gift', bonus_days=gift_days)
        except Exception:
            pass

        # Clear pending
        if user.pending_promo_code and user.pending_promo_code.upper() == promo.code.upper():
            user.pending_promo_code = ''
            user.save(update_fields=['pending_promo_code'])

        # Create local subscription record for tracking
        sub = Subscription.objects.create(
            user=user,
            plan=gift_plan,
            period_months=0,
            price_paid=0,
            payment_method='gift_promo',
            payment_id=f'gift_{promo.code}',
            status='paid',
            expires_at=datetime.now(tz.utc) + timedelta(days=gift_days),
            remnawave_uuid=user.remnawave_uuid,
            promo_code=promo,
        )

        return Response({
            'success': True,
            'days_added': gift_days,
            'plan': gift_plan,
            'expires_at': sub.expires_at.isoformat(),
        })


class PromoInfoView(APIView):
    """GET /api/promo/info/?code=X — public promo info for landing page."""
    permission_classes = [AllowAny]

    def get(self, request):
        code = request.query_params.get('code', '').strip()
        if not code:
            return Response({'valid': False})

        try:
            promo = PromoCode.objects.get(code__iexact=code, is_active=True)
        except PromoCode.DoesNotExist:
            return Response({'valid': False})

        from django.utils import timezone
        if promo.valid_until and promo.valid_until < timezone.now():
            return Response({'valid': False})

        if promo.max_uses > 0 and promo.times_used >= promo.max_uses:
            return Response({'valid': False})

        return Response({
            'valid': True,
            'code': promo.code,
            'promo_type': promo.promo_type,
            'value': promo.value,
            'description': promo.description,
        })


class PurchaseView(APIView):
    """POST /api/subscriptions/purchase/ — initiate purchase."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan = request.data.get('plan')
        period = request.data.get('period')
        method = request.data.get('payment_method')
        crypto_asset = request.data.get('crypto_asset', 'USDT')  # USDT or TON
        promo_code_str = request.data.get('promo_code', '').strip()

        if plan not in PLANS:
            return Response({'error': 'Invalid plan'}, status=400)
        if period not in [1, 3, 6, 12]:
            return Response({'error': 'Invalid period'}, status=400)
        if method not in ['stars', 'crypto', 'wata']:
            return Response({'error': 'Invalid payment method'}, status=400)

        user = request.user
        has_referral = user.referred_by is not None

        # Resolve promo code (explicit > pending)
        if not promo_code_str and user.pending_promo_code:
            promo_code_str = user.pending_promo_code

        promo = None
        bonus_days = 0
        promo_discount = 0

        if promo_code_str:
            promo, error = validate_promo_for_user(user, promo_code_str, plan, period)
            if error:
                return Response({'error': f'Промокод: {error}'}, status=400)
            if promo.promo_type == 'gift':
                return Response({'error': 'Подарочные промокоды активируются без покупки'}, status=400)

        # Calculate price
        base_price = get_price(plan, period)
        referral_discount = round(base_price * 0.10) if has_referral else 0
        after_referral = base_price - referral_discount

        if promo and promo.promo_type == 'percent':
            promo_discount = round(after_referral * promo.value / 100)
        elif promo and promo.promo_type == 'days':
            bonus_days = promo.value

        total_price = max(after_referral - promo_discount, 1)

        # Cancel any stale pending subscriptions for this user
        from datetime import datetime, timedelta, timezone
        Subscription.objects.filter(user=user, status='pending').update(status='cancelled')

        # Create pending subscription
        sub = Subscription.objects.create(
            user=user,
            plan=plan,
            period_months=period,
            price_paid=total_price,
            payment_method=method,
            status='pending',
            expires_at=datetime.now(timezone.utc) + timedelta(days=period * 30),
            promo_code=promo,
        )

        # Create invoice based on payment method
        if method == 'stars':
            invoice = create_stars_invoice(sub, total_price)
        elif method == 'crypto':
            invoice = create_crypto_invoice(sub, total_price, crypto_asset)
        elif method == 'wata':
            invoice = create_wata_invoice(sub, total_price)
        else:
            return Response({'error': 'Unknown method'}, status=400)

        if invoice.get('error'):
            sub.delete()
            return Response({'error': invoice['error']}, status=500)

        sub.payment_id = invoice.get('payment_id', '')
        sub.save()

        # Admin notification: new deal
        try:
            from .admin_notify import notify_payment_initiated
            notify_payment_initiated(user, sub, total_price, method, crypto_asset if method == 'crypto' else None)
        except Exception:
            pass

        return Response({
            'subscription_id': sub.id,
            'payment_url': invoice.get('payment_url'),
            'payment_id': invoice.get('payment_id'),
            'method': method,
            'amount': total_price,
            'promo_applied': promo.code if promo else None,
            'promo_discount': promo_discount,
            'bonus_days': bonus_days,
        })


class MySubscriptionView(APIView):
    """GET /api/subscriptions/my/ — current subscription + Remnawave traffic data."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        sub = user.subscriptions.filter(status='paid').order_by('-expires_at').first()
        if not sub:
            return Response({'subscription': None})

        plan_config = PLANS.get(sub.plan, {})

        data = {
            'id': sub.id,
            'plan': sub.plan,
            'plan_name': plan_config.get('name', sub.plan),
            'period_months': sub.period_months,
            'price_paid': str(sub.price_paid),
            'status': sub.status,
            'payment_method': sub.payment_method,
            'created_at': sub.created_at.isoformat(),
            'expires_at': sub.expires_at.isoformat(),
            'subscription_url': user.subscription_url,
            # Plan details
            'plan_servers': plan_config.get('servers', 0),
            'plan_devices': plan_config.get('devices', 0),
            'plan_traffic_bytes': plan_config.get('traffic_bytes', 0),
            'plan_adblock': plan_config.get('adblock', False),
            'plan_p2p': plan_config.get('p2p', False),
            # Remnawave live data
            'remnawave': None,
        }

        # Fetch live data from Remnawave
        if user.remnawave_uuid:
            try:
                rmn = remnawave.get_user_data(user.remnawave_uuid)
                if rmn:
                    traffic = rmn.get('userTraffic', {})
                    data['remnawave'] = {
                        'status': rmn.get('status', 'UNKNOWN'),
                        'used_traffic_bytes': traffic.get('usedTrafficBytes', 0),
                        'lifetime_traffic_bytes': traffic.get('lifetimeUsedTrafficBytes', 0),
                        'traffic_limit_bytes': rmn.get('trafficLimitBytes', 0),
                        'online_at': traffic.get('onlineAt'),
                        'first_connected_at': traffic.get('firstConnectedAt'),
                        'last_node_uuid': traffic.get('lastConnectedNodeUuid'),
                        'hwid_device_limit': rmn.get('hwidDeviceLimit', 0),
                        'expire_at': rmn.get('expireAt'),
                        'last_traffic_reset_at': rmn.get('lastTrafficResetAt'),
                    }
                    # Backfill subscription_url if missing
                    rmn_sub_url = rmn.get('subscriptionUrl', '')
                    if rmn_sub_url and not user.subscription_url:
                        user.subscription_url = rmn_sub_url
                        user.save(update_fields=['subscription_url'])
                    if rmn_sub_url:
                        data['subscription_url'] = rmn_sub_url
            except Exception:
                pass

        return Response({'subscription': data})


class UserDevicesView(APIView):
    """GET /api/subscriptions/devices/ — user's HWID devices from Remnawave DB.
       DELETE /api/subscriptions/devices/ — remove a device by HWID."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.remnawave_uuid:
            return Response({'devices': []})

        devices = remnawave.get_user_devices(user.remnawave_uuid)
        return Response({'devices': devices})

    def delete(self, request):
        user = request.user
        hwid = request.data.get('hwid', '').strip()

        if not user.remnawave_uuid:
            return Response({'error': 'Нет активной подписки'}, status=400)
        if not hwid:
            return Response({'error': 'HWID обязателен'}, status=400)

        success = remnawave.delete_user_device(user.remnawave_uuid, hwid)
        if success:
            return Response({'success': True})
        return Response({'error': 'Устройство не найдено'}, status=404)


class TrialActivateView(APIView):
    """POST /api/subscriptions/trial/ — activate 3-day MAX trial."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.db import transaction
        from datetime import datetime, timedelta, timezone

        with transaction.atomic():
            # Lock user row to prevent race condition
            from accounts.models import User
            user = User.objects.select_for_update().get(pk=request.user.pk)

            if user.used_trial:
                return Response({'error': 'Триал уже был использован'}, status=400)
            if user.subscriptions.exists():
                return Response({'error': 'У вас уже есть или была подписка'}, status=400)

            # Create Remnawave subscription (MAX, 3 days)
            try:
                rmn_user = remnawave.create_subscription(user, 'max', period_months=0, days=3)
                user.remnawave_uuid = rmn_user['uuid']
                user.remnawave_short_uuid = rmn_user['shortUuid']
                user.subscription_url = rmn_user.get('subscriptionUrl', '')
                user.used_trial = True
                user.save()
            except Exception as e:
                return Response({'error': f'Ошибка создания подписки: {str(e)}'}, status=500)

            # Create local subscription record
            sub = Subscription.objects.create(
                user=user,
                plan='max',
                period_months=0,
                price_paid=0,
                payment_method='trial',
                payment_id='trial_3d_max',
                status='paid',
                expires_at=datetime.now(timezone.utc) + timedelta(days=3),
                remnawave_uuid=rmn_user['uuid'],
            )

        return Response({
            'success': True,
            'plan': 'max',
            'days': 3,
            'subscription_url': user.subscription_url,
            'expires_at': sub.expires_at.isoformat(),
        })


class TrialUpgradeView(APIView):
    """POST /api/subscriptions/trial-upgrade/ — 7 days PRO for 1₽."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.db import transaction
        from datetime import datetime, timedelta, timezone
        from accounts.models import User

        method = request.data.get('payment_method', 'stars')
        if method not in ('stars', 'crypto', 'wata'):
            return Response({'error': 'Invalid payment method'}, status=400)

        with transaction.atomic():
            # Lock user row to prevent race condition
            user = User.objects.select_for_update().get(pk=request.user.pk)

            if not user.used_trial:
                return Response({'error': 'Сначала активируйте триал'}, status=400)
            if user.used_trial_upgrade:
                return Response({'error': 'Спецпредложение уже использовано'}, status=400)

            # Cancel any stale pending upgrade subscriptions
            Subscription.objects.filter(user=user, price_paid=1, status='pending').update(status='cancelled')

            # Create pending subscription
            sub = Subscription.objects.create(
                user=user,
                plan='pro',
                period_months=0,
                price_paid=1,
                payment_method=method,
                status='pending',
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )

        # Create invoice for 1₽ (outside transaction — external API call)
        if method == 'stars':
            invoice = create_stars_invoice(sub, 1)
        elif method == 'crypto':
            invoice = create_crypto_invoice(sub, 1)
        elif method == 'wata':
            invoice = create_wata_invoice(sub, 1)

        if invoice.get('error'):
            sub.delete()
            return Response({'error': invoice['error']}, status=500)

        sub.payment_id = invoice.get('payment_id', '')
        sub.save()

        return Response({
            'payment_url': invoice.get('payment_url'),
            'payment_id': invoice.get('payment_id'),
            'amount': 1,
            'method': method,
        })


# === Payment method helpers ===

def create_stars_invoice(sub, amount_rub):
    """Create Telegram Stars invoice via Bot API.

    Uses dynamic USDT/RUB rate: 50 stars = 0.75$ + 15% markup.
    """
    bot_token = settings.TELEGRAM_BOT_TOKEN
    stars_amount = rub_to_stars(amount_rub)

    try:
        resp = requests.post(
            f'https://api.telegram.org/bot{bot_token}/createInvoiceLink',
            json={
                'title': f'EIFAVPN {PLANS[sub.plan]["name"]} — {sub.period_months} мес',
                'description': f'VPN подписка {PLANS[sub.plan]["name"]} на {sub.period_months} мес.',
                'payload': json.dumps({'sub_id': sub.id}),
                'currency': 'XTR',
                'prices': [{'label': 'VPN подписка', 'amount': stars_amount}],
            },
            timeout=10,
        )
        data = resp.json()
        if data.get('ok'):
            return {'payment_url': data['result'], 'payment_id': f'stars_{sub.id}'}
        return {'error': data.get('description', 'Stars invoice failed')}
    except Exception as e:
        return {'error': str(e)}


def create_crypto_invoice(sub, amount_rub, crypto_asset='USDT'):
    """Create CryptoPay invoice in specific cryptocurrency.

    If crypto_asset specified: creates invoice in that crypto (converted from RUB + 3% markup).
    Otherwise: creates fiat RUB invoice with multi-asset selection.
    """
    token = settings.CRYPTOPAY_TOKEN

    # Convert RUB to specific crypto
    if crypto_asset and crypto_asset in ('USDT', 'TON'):
        crypto_amount = rub_to_crypto(amount_rub, crypto_asset)
        if crypto_amount <= 0:
            return {'error': 'Не удалось получить курс валюты'}
        invoice_json = {
            'currency_type': 'crypto',
            'asset': crypto_asset,
            'amount': str(crypto_amount),
            'description': f'EIFAVPN {PLANS[sub.plan]["name"]} — {sub.period_months} мес',
            'payload': json.dumps({'sub_id': sub.id}),
            'expires_in': 3600,
            'paid_btn_name': 'callback',
            'paid_btn_url': f'{settings.APP_URL}/cabinet/overview',
        }
    else:
        # Fallback: fiat RUB with multi-asset
        invoice_json = {
            'currency_type': 'fiat',
            'fiat': 'RUB',
            'amount': str(amount_rub),
            'accepted_assets': 'USDT,TON,BTC',
            'description': f'EIFAVPN {PLANS[sub.plan]["name"]} — {sub.period_months} мес',
            'payload': json.dumps({'sub_id': sub.id}),
            'expires_in': 3600,
            'paid_btn_name': 'callback',
            'paid_btn_url': f'{settings.APP_URL}/cabinet/overview',
        }

    try:
        resp = requests.post(
            'https://pay.crypt.bot/api/createInvoice',
            headers={
                'Crypto-Pay-API-Token': token,
                'User-Agent': 'EIFAVPN/1.0',
            },
            json=invoice_json,
            timeout=10,
        )
        data = resp.json()
        if data.get('ok'):
            invoice = data['result']
            return {
                'payment_url': invoice.get('bot_invoice_url') or invoice.get('mini_app_invoice_url'),
                'payment_id': str(invoice['invoice_id']),
            }
        return {'error': data.get('error', {}).get('name', 'CryptoPay failed')}
    except Exception as e:
        return {'error': str(e)}


def create_wata_invoice(sub, amount_rub):
    """Create Wata H2H payment link.

    API: POST https://api.wata.pro/api/h2h/links/
    Amount in RUBLES (not kopecks!), camelCase field names.
    """
    token = settings.WATA_TOKEN

    try:
        resp = requests.post(
            'https://api.wata.pro/api/h2h/links/',
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'User-Agent': 'EIFAVPN/1.0',
            },
            json={
                'amount': round(float(amount_rub), 2),
                'currency': 'RUB',
                'orderId': f'eifavpn_{sub.id}',
                'description': f'EIFAVPN {PLANS[sub.plan]["name"]} — {sub.period_months} мес',
                'successRedirectUrl': f'{settings.APP_URL}/cabinet/overview',
                'failRedirectUrl': f'{settings.APP_URL}/cabinet/purchase?failed=1',
            },
            timeout=15,
        )
        data = resp.json()
        if data.get('id'):
            return {
                'payment_url': data.get('url'),
                'payment_id': data['id'],
            }
        return {'error': data.get('message', data.get('title', 'Wata payment failed'))}
    except Exception as e:
        return {'error': str(e)}


# === Webhooks ===

def process_payment_success(sub):
    """After successful payment: create or update Remnawave subscription + referral bonus."""
    user = sub.user

    try:
        if user.remnawave_uuid:
            # User already has a Remnawave account — UPDATE plan (squad, traffic, devices, expiry)
            rmn_user = remnawave.update_subscription(
                user.remnawave_uuid, sub.plan, sub.period_months
            )
            sub.remnawave_uuid = user.remnawave_uuid
        else:
            # New user — CREATE Remnawave subscription
            rmn_user = remnawave.create_subscription(user, sub.plan, sub.period_months)
            user.remnawave_uuid = rmn_user['uuid']
            user.remnawave_short_uuid = rmn_user['shortUuid']
            user.subscription_url = rmn_user.get('subscriptionUrl', '')
            user.save()
            sub.remnawave_uuid = rmn_user['uuid']
    except Exception as e:
        import logging
        logging.error(f'Remnawave subscription error for user {user.id}: {e}')
        pass

    sub.status = 'paid'
    sub.save()

    # Mark trial upgrade as used after successful payment (atomic to prevent race)
    if sub.payment_method in ('stars', 'crypto', 'wata') and sub.price_paid == 1:
        from accounts.models import User
        User.objects.filter(pk=user.pk, used_trial_upgrade=False).update(used_trial_upgrade=True)
        user.refresh_from_db()

    # Promo code: apply bonus days + record usage
    if sub.promo_code:
        promo = sub.promo_code
        bonus_days = 0
        discount_amount = 0

        if promo.promo_type == 'days' and user.remnawave_uuid:
            bonus_days = promo.value
            try:
                remnawave.extend_subscription(user.remnawave_uuid, bonus_days)
            except Exception:
                pass
        elif promo.promo_type == 'percent':
            base = get_price(sub.plan, sub.period_months)
            discount_amount = base - float(sub.price_paid)

        PromoCodeUsage.objects.create(
            promo=promo, user=user, subscription=sub,
            discount_amount=discount_amount, bonus_days=bonus_days,
        )
        PromoCode.objects.filter(pk=promo.pk).update(times_used=F('times_used') + 1)

        try:
            from .admin_notify import notify_promo_applied
            notify_promo_applied(user, promo, context='purchase', discount=discount_amount, bonus_days=bonus_days)
        except Exception:
            pass

        # Clear pending promo
        if user.pending_promo_code:
            user.pending_promo_code = ''
            user.save(update_fields=['pending_promo_code'])

    # Referral bonus: +7 days for the person who invited this user
    if user.referred_by and not Referral.objects.filter(referred=user, bonus_applied=True).exists():
        referrer = user.referred_by
        if referrer.remnawave_uuid:
            try:
                remnawave.extend_subscription(referrer.remnawave_uuid, REFERRAL_BONUS_DAYS)
                referrer.referral_bonus_days += REFERRAL_BONUS_DAYS
                referrer.save()
            except Exception:
                pass
        Referral.objects.create(
            referrer=referrer,
            referred=user,
            subscription=sub,
            bonus_applied=True,
        )

    # Telegram notification about successful purchase
    try:
        from .notifications import notify_purchase_success
        notify_purchase_success(user, sub)
        from .admin_notify import notify_payment_success
        notify_payment_success(sub)
    except Exception:
        pass


@csrf_exempt
def webhook_stars(request):
    """Telegram Bot API webhook for Stars payments."""
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)

    try:
        data = json.loads(request.body)

        # Handle pre_checkout_query — always approve
        if 'pre_checkout_query' in data:
            query = data['pre_checkout_query']
            requests.post(
                f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/answerPreCheckoutQuery',
                json={'pre_checkout_query_id': query['id'], 'ok': True},
                timeout=5,
            )
            return JsonResponse({'ok': True})

        # Handle /start command — send welcome
        message = data.get('message', {})
        text = message.get('text', '')
        if text and text.startswith('/start'):
            chat_id = message.get('chat', {}).get('id')
            first_name = message.get('from', {}).get('first_name', '')
            if chat_id:
                from .notifications import send_welcome
                send_welcome(chat_id, first_name)
            return JsonResponse({'ok': True})

        # Handle successful_payment
        payment = message.get('successful_payment')
        if payment:
            payload = json.loads(payment.get('invoice_payload', '{}'))
            sub_id = payload.get('sub_id')
            if sub_id:
                sub = Subscription.objects.filter(id=sub_id, status='pending').first()
                if sub:
                    sub.payment_id = payment.get('telegram_payment_charge_id', '')
                    process_payment_success(sub)

        return JsonResponse({'ok': True})
    except Exception:
        return JsonResponse({'ok': False}, status=500)


@csrf_exempt
def webhook_crypto(request):
    """CryptoPay webhook for crypto payments."""
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)

    try:
        # Verify signature
        signature = request.headers.get('crypto-pay-api-signature', '')
        secret = hashlib.sha256(settings.CRYPTOPAY_TOKEN.encode()).digest()
        expected = hmac.new(secret, request.body, hashlib.sha256).hexdigest()

        if signature != expected:
            return JsonResponse({'error': 'Invalid signature'}, status=403)

        data = json.loads(request.body)
        if data.get('update_type') != 'invoice_paid':
            return JsonResponse({'ok': True})

        invoice = data.get('payload', {})
        payload = json.loads(invoice.get('payload', '{}'))
        sub_id = payload.get('sub_id')

        if sub_id:
            sub = Subscription.objects.filter(id=sub_id, status='pending').first()
            if sub:
                sub.payment_id = str(invoice.get('invoice_id', ''))
                process_payment_success(sub)

        return JsonResponse({'ok': True})
    except Exception:
        return JsonResponse({'ok': False}, status=500)


@csrf_exempt
def webhook_wata(request):
    """Wata H2H webhook for card/SBP payments.

    Payload: {transactionStatus, orderId, transactionId, amount, ...}
    orderId format: "eifavpn_{sub_id}"
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)

    try:
        data = json.loads(request.body)
        order_id = data.get('orderId', '')
        tx_status = data.get('transactionStatus', '')
        tx_id = data.get('transactionId', '')

        import logging
        logging.info(f'Wata webhook: orderId={order_id} status={tx_status} txId={tx_id}')

        if tx_status == 'Paid' and order_id.startswith('eifavpn_'):
            sub_id = order_id.replace('eifavpn_', '')
            sub = Subscription.objects.filter(id=sub_id, status='pending').first()
            if sub:
                sub.payment_id = tx_id or data.get('id', '')
                process_payment_success(sub)

        return JsonResponse({'ok': True})
    except Exception as e:
        import logging
        logging.error(f'Wata webhook error: {e}')
        return JsonResponse({'ok': False}, status=500)
