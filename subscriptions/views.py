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

from accounts.models import Subscription, Referral
from .plans import PLANS, PRICING, get_price, get_price_with_referral, REFERRAL_BONUS_DAYS
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


class PurchaseView(APIView):
    """POST /api/subscriptions/purchase/ — initiate purchase."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan = request.data.get('plan')
        period = request.data.get('period')
        method = request.data.get('payment_method')

        if plan not in PLANS:
            return Response({'error': 'Invalid plan'}, status=400)
        if period not in [1, 3, 6, 12]:
            return Response({'error': 'Invalid period'}, status=400)
        if method not in ['stars', 'crypto', 'wata']:
            return Response({'error': 'Invalid payment method'}, status=400)

        user = request.user
        has_referral = user.referred_by is not None
        total_price = get_price_with_referral(plan, period) if has_referral else get_price(plan, period)

        # Create pending subscription
        from datetime import datetime, timedelta, timezone
        sub = Subscription.objects.create(
            user=user,
            plan=plan,
            period_months=period,
            price_paid=total_price,
            payment_method=method,
            status='pending',
            expires_at=datetime.now(timezone.utc) + timedelta(days=period * 30),
        )

        # Create invoice based on payment method
        if method == 'stars':
            invoice = create_stars_invoice(sub, total_price)
        elif method == 'crypto':
            invoice = create_crypto_invoice(sub, total_price)
        elif method == 'wata':
            invoice = create_wata_invoice(sub, total_price)
        else:
            return Response({'error': 'Unknown method'}, status=400)

        if invoice.get('error'):
            sub.delete()
            return Response({'error': invoice['error']}, status=500)

        sub.payment_id = invoice.get('payment_id', '')
        sub.save()

        return Response({
            'subscription_id': sub.id,
            'payment_url': invoice.get('payment_url'),
            'payment_id': invoice.get('payment_id'),
            'method': method,
            'amount': total_price,
        })


class MySubscriptionView(APIView):
    """GET /api/subscriptions/my/ — current user subscription."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sub = request.user.subscriptions.filter(status='paid').order_by('-expires_at').first()
        if not sub:
            return Response({'subscription': None})

        data = {
            'id': sub.id,
            'plan': sub.plan,
            'plan_name': PLANS[sub.plan]['name'],
            'period_months': sub.period_months,
            'price_paid': str(sub.price_paid),
            'status': sub.status,
            'payment_method': sub.payment_method,
            'created_at': sub.created_at.isoformat(),
            'expires_at': sub.expires_at.isoformat(),
            'subscription_url': request.user.subscription_url,
        }
        return Response({'subscription': data})


class TrialActivateView(APIView):
    """POST /api/subscriptions/trial/ — activate 3-day MAX trial."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.used_trial:
            return Response({'error': 'Триал уже был использован'}, status=400)
        if user.subscriptions.exists():
            return Response({'error': 'У вас уже есть или была подписка'}, status=400)

        from datetime import datetime, timedelta, timezone

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
        user = request.user
        method = request.data.get('payment_method', 'stars')

        if not user.used_trial:
            return Response({'error': 'Сначала активируйте триал'}, status=400)
        if user.used_trial_upgrade:
            return Response({'error': 'Спецпредложение уже использовано'}, status=400)

        from datetime import datetime, timedelta, timezone

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

        # Create invoice for 1₽
        if method == 'stars':
            invoice = create_stars_invoice(sub, 1)
        elif method == 'crypto':
            invoice = create_crypto_invoice(sub, 1)
        elif method == 'wata':
            invoice = create_wata_invoice(sub, 1)
        else:
            sub.delete()
            return Response({'error': 'Invalid payment method'}, status=400)

        if invoice.get('error'):
            sub.delete()
            return Response({'error': invoice['error']}, status=500)

        sub.payment_id = invoice.get('payment_id', '')
        sub.save()

        # Mark trial upgrade as used (will be confirmed on payment)
        user.used_trial_upgrade = True
        user.save()

        return Response({
            'payment_url': invoice.get('payment_url'),
            'payment_id': invoice.get('payment_id'),
            'amount': 1,
        })


# === Payment method helpers ===

def create_stars_invoice(sub, amount_rub):
    """Create Telegram Stars invoice via Bot API."""
    bot_token = settings.TELEGRAM_BOT_TOKEN
    # Convert RUB to Stars (approximate: 1 Star ≈ 1.5 RUB)
    stars_amount = max(1, round(amount_rub / 1.5))

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


def create_crypto_invoice(sub, amount_rub):
    """Create CryptoPay invoice."""
    token = settings.CRYPTOPAY_TOKEN

    try:
        resp = requests.post(
            'https://pay.crypt.bot/api/createInvoice',
            headers={'Crypto-Pay-API-Token': token},
            json={
                'currency_type': 'fiat',
                'fiat': 'RUB',
                'amount': str(amount_rub),
                'accepted_assets': 'USDT,TON,BTC',
                'description': f'EIFAVPN {PLANS[sub.plan]["name"]} — {sub.period_months} мес',
                'payload': json.dumps({'sub_id': sub.id}),
                'expires_in': 3600,
                'paid_btn_name': 'callback',
                'paid_btn_url': f'{settings.APP_URL}/cabinet/overview',
            },
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
    """Create WataApi H2H payment link."""
    token = settings.WATA_TOKEN

    try:
        resp = requests.post(
            'https://api.wata.pro/api/h2h/link',
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            json={
                'amount': amount_rub * 100,  # kopecks
                'description': f'EIFAVPN {PLANS[sub.plan]["name"]} — {sub.period_months} мес',
                'order_id': str(sub.id),
                'success_url': f'{settings.APP_URL}/cabinet/overview',
                'fail_url': f'{settings.APP_URL}/cabinet/purchase?failed=1',
            },
            timeout=10,
        )
        data = resp.json()
        if resp.ok:
            return {
                'payment_url': data.get('payment_url') or data.get('url'),
                'payment_id': data.get('id', str(sub.id)),
            }
        return {'error': 'WataApi failed'}
    except Exception as e:
        return {'error': str(e)}


# === Webhooks ===

def process_payment_success(sub):
    """After successful payment: create Remnawave subscription + referral bonus."""
    user = sub.user

    # Create VPN subscription in Remnawave
    try:
        rmn_user = remnawave.create_subscription(user, sub.plan, sub.period_months)
        user.remnawave_uuid = rmn_user['uuid']
        user.remnawave_short_uuid = rmn_user['shortUuid']
        user.subscription_url = rmn_user.get('subscriptionUrl', '')
        user.save()
        sub.remnawave_uuid = rmn_user['uuid']
    except Exception:
        # Log error but don't fail — can be retried
        pass

    sub.status = 'paid'
    sub.save()

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

        # Handle successful_payment
        message = data.get('message', {})
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
    """WataApi webhook for card payments."""
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)

    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        status = data.get('status')

        if status == 'success' and order_id:
            sub = Subscription.objects.filter(id=order_id, status='pending').first()
            if sub:
                sub.payment_id = data.get('id', '')
                process_payment_success(sub)

        return JsonResponse({'ok': True})
    except Exception:
        return JsonResponse({'ok': False}, status=500)
