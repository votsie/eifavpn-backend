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
from accounts.models import Subscription, Referral
try:
    from accounts.models import PromoCode, PromoCodeUsage
except ImportError:
    PromoCode = None
    PromoCodeUsage = None
from .plans import PLANS, PRICING, get_price, get_price_with_referral, REFERRAL_BONUS_DAYS, get_upgrade_price
try:
    from .promo_utils import validate_promo_for_user, calculate_promo_price
except ImportError:
    validate_promo_for_user = None
    calculate_promo_price = None
try:
    from .exchange_rates import get_rates, rub_to_crypto, rub_to_stars
except ImportError:
    get_rates = None
    rub_to_crypto = None
    rub_to_stars = None
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
        try:
            amount = float(request.query_params.get('amount', 0))
        except (TypeError, ValueError):
            amount = 0
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
        if validate_promo_for_user is None:
            return Response({'valid': False, 'error': 'Промокоды не доступны'})

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
        if validate_promo_for_user is None:
            return Response({'error': 'Промокоды не доступны'}, status=501)

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
        if not code or PromoCode is None:
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
        try:
            period = int(period)
        except (TypeError, ValueError):
            return Response({'error': 'Invalid period'}, status=400)
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

        # Create pending subscription (expires_at is placeholder — recalculated on payment success)
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


class UpgradePreviewView(APIView):
    """GET /api/subscriptions/upgrade-preview/?plan=X&period=Y — calculate upgrade cost."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        new_plan = request.query_params.get('plan')
        new_period = request.query_params.get('period')

        if not new_plan or new_plan not in PLANS:
            return Response({'error': 'Invalid plan'}, status=400)
        try:
            new_period = int(new_period)
        except (TypeError, ValueError):
            return Response({'error': 'Invalid period'}, status=400)
        if new_period not in (1, 3, 6, 12):
            return Response({'error': 'Invalid period'}, status=400)

        user = request.user
        from django.utils import timezone
        active_sub = user.subscriptions.filter(
            status='paid', expires_at__gt=timezone.now()
        ).order_by('-expires_at').first()

        if not active_sub:
            return Response({'error': 'Нет активной подписки для смены тарифа'}, status=400)

        if active_sub.plan == new_plan and active_sub.period_months == new_period:
            return Response({'error': 'Вы уже на этом тарифе'}, status=400)

        result = get_upgrade_price(active_sub, new_plan, new_period)
        result['current_plan'] = active_sub.plan
        result['current_period'] = active_sub.period_months
        result['new_plan'] = new_plan
        result['new_period'] = new_period
        return Response(result)


class UpgradeView(APIView):
    """POST /api/subscriptions/upgrade/ — initiate plan upgrade/downgrade."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        new_plan = request.data.get('plan')
        new_period = request.data.get('period')
        method = request.data.get('payment_method', 'stars')
        crypto_asset = request.data.get('crypto_asset', 'USDT')

        if not new_plan or new_plan not in PLANS:
            return Response({'error': 'Invalid plan'}, status=400)
        try:
            new_period = int(new_period)
        except (TypeError, ValueError):
            return Response({'error': 'Invalid period'}, status=400)
        if new_period not in (1, 3, 6, 12):
            return Response({'error': 'Invalid period'}, status=400)

        user = request.user
        from datetime import datetime, timedelta, timezone
        now_dt = datetime.now(timezone.utc)

        active_sub = user.subscriptions.filter(
            status='paid', expires_at__gt=now_dt
        ).order_by('-expires_at').first()

        if not active_sub:
            return Response({'error': 'Нет активной подписки'}, status=400)

        calc = get_upgrade_price(active_sub, new_plan, new_period)

        if calc['is_upgrade'] and calc['charge_amount'] > 0:
            # Upgrade: create pending sub, generate invoice for difference
            sub = Subscription.objects.create(
                user=user,
                plan=new_plan,
                period_months=new_period,
                price_paid=calc['charge_amount'],
                payment_method=method,
                status='pending',
                expires_at=now_dt + timedelta(days=new_period * 30),
                upgrade_from=active_sub,
            )

            if method == 'stars':
                invoice = create_stars_invoice(sub, calc['charge_amount'])
            elif method == 'crypto':
                invoice = create_crypto_invoice(sub, calc['charge_amount'], crypto_asset)
            elif method == 'wata':
                invoice = create_wata_invoice(sub, calc['charge_amount'])
            else:
                sub.delete()
                return Response({'error': 'Invalid payment method'}, status=400)

            if invoice.get('error'):
                sub.delete()
                return Response({'error': invoice['error']}, status=500)

            sub.payment_id = invoice.get('payment_id', '')
            sub.save(update_fields=['payment_id'])

            return Response({
                'type': 'upgrade',
                'charge_amount': calc['charge_amount'],
                'payment_url': invoice.get('payment_url'),
                'payment_id': invoice.get('payment_id'),
                'subscription_id': sub.id,
            })
        else:
            # Downgrade or free switch: apply immediately
            try:
                remnawave.update_subscription(user.remnawave_uuid, new_plan, new_period)
            except Exception as e:
                return Response({'error': f'Remnawave error: {str(e)}'}, status=500)

            # Create paid sub record
            sub = Subscription.objects.create(
                user=user,
                plan=new_plan,
                period_months=new_period,
                price_paid=0,
                payment_method='downgrade',
                status='paid',
                expires_at=now_dt + timedelta(days=new_period * 30),
                upgrade_from=active_sub,
            )

            # Apply credit as bonus days
            if calc['credit_days'] > 0 and user.remnawave_uuid:
                try:
                    remnawave.extend_subscription(user.remnawave_uuid, calc['credit_days'])
                except Exception:
                    pass

            return Response({
                'type': 'downgrade',
                'credit_days': calc['credit_days'],
                'new_plan': new_plan,
                'applied': True,
            })


class PaymentHistoryView(APIView):
    """GET /api/subscriptions/history/ — user's payment history."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        subs = request.user.subscriptions.filter(
            status__in=['paid', 'cancelled', 'expired']
        ).order_by('-created_at')

        result = []
        for s in subs[:50]:
            result.append({
                'id': s.id,
                'plan': s.plan,
                'plan_name': PLANS.get(s.plan, {}).get('name', s.plan),
                'period_months': s.period_months,
                'price_paid': str(s.price_paid),
                'payment_method': s.payment_method,
                'status': s.status,
                'created_at': s.created_at.isoformat(),
                'expires_at': s.expires_at.isoformat(),
            })
        return Response(result)


# === Payment method helpers (extracted to subscriptions/invoices.py) ===

from .invoices import create_stars_invoice, create_crypto_invoice, create_wata_invoice


# === Webhooks ===

def process_payment_success(sub):
    """After successful payment: create or update Remnawave subscription + referral bonus.

    Idempotent: uses select_for_update to prevent double-processing from duplicate webhooks.
    """
    import logging
    from datetime import datetime, timedelta, timezone
    from django.db import transaction

    logger = logging.getLogger(__name__)

    with transaction.atomic():
        # Lock the subscription row — prevents double webhook processing
        sub = Subscription.objects.select_for_update().get(pk=sub.pk)

        # Idempotency: if already paid, do nothing
        if sub.status == 'paid':
            logger.info(f'Subscription {sub.pk} already paid, skipping duplicate webhook')
            return

        user = sub.user

        # Recalculate expires_at from NOW (payment time)
        if sub.period_months > 0:
            sub.expires_at = datetime.now(timezone.utc) + timedelta(days=sub.period_months * 30)

        # Provision VPN access via Remnawave
        remnawave_ok = False
        try:
            if user.remnawave_uuid:
                rmn_user = remnawave.update_subscription(
                    user.remnawave_uuid, sub.plan, sub.period_months
                )
                sub.remnawave_uuid = user.remnawave_uuid
            else:
                rmn_user = remnawave.create_subscription(user, sub.plan, sub.period_months)
                user.remnawave_uuid = rmn_user['uuid']
                user.remnawave_short_uuid = rmn_user['shortUuid']
                user.subscription_url = rmn_user.get('subscriptionUrl', '')
                user.save()
                sub.remnawave_uuid = rmn_user['uuid']
            remnawave_ok = True
        except Exception as e:
            logger.error(f'CRITICAL: Remnawave failed for sub {sub.pk} user {user.id}: {e}')

        if not remnawave_ok:
            # Don't mark as paid if VPN access wasn't provisioned
            sub.status = 'error'
            sub.save(update_fields=['status', 'expires_at'])
            # Notify admin about the failure
            try:
                from .admin_notify import notify_payment_success
            except ImportError:
                pass
            return

        sub.status = 'paid'
        sub.save()

        # If this is a plan upgrade, cancel the old subscription
        if sub.upgrade_from and sub.upgrade_from.status == 'paid':
            sub.upgrade_from.status = 'cancelled'
            sub.upgrade_from.save(update_fields=['status'])

        # If this is a renewal, clean up payment_method prefix
        if sub.payment_method.startswith('renewal_'):
            sub.payment_method = sub.payment_method.replace('renewal_', '')
            sub.save(update_fields=['payment_method'])

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

    # Verify webhook secret token (set via setWebhook secret_token param)
    # Fail-closed: always require webhook secret in production
    webhook_secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '')
    if not webhook_secret and not getattr(settings, 'DEBUG', False):
        import logging
        logging.error('TELEGRAM_WEBHOOK_SECRET not configured — rejecting Stars webhook')
        return JsonResponse({'ok': False, 'error': 'Webhook secret not configured'}, status=500)
    if webhook_secret:
        received_secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        if received_secret != webhook_secret:
            return JsonResponse({'ok': False, 'error': 'Invalid secret'}, status=403)

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

        # Handle /connect command — send QR code with subscription link
        if text and text.startswith('/connect'):
            from_user = message.get('from', {})
            telegram_id = from_user.get('id')
            chat_id = message.get('chat', {}).get('id')
            if telegram_id and chat_id:
                _handle_connect_command(telegram_id, chat_id)
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
                    sub.save(update_fields=['payment_id'])
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
                sub.save(update_fields=['payment_id'])
                process_payment_success(sub)

        return JsonResponse({'ok': True})
    except Exception:
        return JsonResponse({'ok': False}, status=500)


@csrf_exempt
def webhook_wata(request):
    """Wata H2H webhook for card/SBP payments.

    Payload: {transactionStatus, orderId, transactionId, amount, ...}
    orderId format: "eifavpn_{sub_id}"

    Security: verify payment by calling Wata API to confirm transaction status
    (server-to-server verification — don't trust webhook body alone).
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)

    try:
        data = json.loads(request.body)
        order_id = data.get('orderId', '')
        tx_status = data.get('transactionStatus', '')
        tx_id = data.get('transactionId', '') or data.get('id', '')

        import logging
        logging.info(f'Wata webhook: orderId={order_id} status={tx_status} txId={tx_id}')

        if tx_status == 'Paid' and order_id.startswith('eifavpn_'):
            sub_id = order_id.replace('eifavpn_', '')
            sub = Subscription.objects.filter(id=sub_id, status='pending').first()
            if sub and tx_id:
                # Server-to-server verification: confirm payment via Wata API
                verified = _verify_wata_payment(tx_id, float(sub.price_paid))
                if not verified:
                    logging.warning(f'Wata webhook: payment verification failed for txId={tx_id}')
                    return JsonResponse({'ok': False, 'error': 'Payment verification failed'}, status=403)

                sub.payment_id = tx_id
                process_payment_success(sub)

        return JsonResponse({'ok': True})
    except Exception as e:
        import logging
        logging.error(f'Wata webhook error: {e}')
        return JsonResponse({'ok': False}, status=500)


def _verify_wata_payment(transaction_id, expected_amount):
    """Verify payment by calling Wata API to confirm transaction status and amount."""
    token = settings.WATA_TOKEN
    if not token:
        return False
    try:
        resp = requests.get(
            f'https://api.wata.pro/api/h2h/links/{transaction_id}',
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            timeout=10,
        )
        if not resp.ok:
            return False
        data = resp.json()
        # Verify status is paid and amount matches
        if data.get('transactionStatus') != 'Paid':
            return False
        paid_amount = float(data.get('amount', 0))
        if abs(paid_amount - expected_amount) > 1:  # Allow 1 RUB tolerance
            return False
        return True
    except Exception:
        # If verification API is down, reject — fail closed
        return False


def _handle_connect_command(telegram_id, chat_id):
    """Handle /connect bot command: send QR code with subscription link."""
    from accounts.models import User
    import logging

    bot_token = settings.TELEGRAM_BOT_TOKEN
    user = User.objects.filter(telegram_id=telegram_id).first()

    if not user:
        requests.post(
            f'https://api.telegram.org/bot{bot_token}/sendMessage',
            json={
                'chat_id': chat_id,
                'text': 'Аккаунт не найден. Зарегистрируйтесь через приложение.',
                'parse_mode': 'HTML',
            },
            timeout=10,
        )
        return

    sub_url = user.subscription_url
    if not sub_url:
        requests.post(
            f'https://api.telegram.org/bot{bot_token}/sendMessage',
            json={
                'chat_id': chat_id,
                'text': 'У вас нет активной подписки. Оформите подписку в приложении.',
                'parse_mode': 'HTML',
                'reply_markup': {
                    'inline_keyboard': [[{
                        'text': 'Открыть EIFAVPN',
                        'url': 'https://t.me/eifavpn_bot/eifavpn',
                    }]]
                },
            },
            timeout=10,
        )
        return

    # Generate QR code
    from .qr_utils import generate_qr_code
    qr_buf = generate_qr_code(sub_url)

    if qr_buf:
        # Send QR as photo
        try:
            requests.post(
                f'https://api.telegram.org/bot{bot_token}/sendPhoto',
                data={
                    'chat_id': chat_id,
                    'caption': (
                        '<b>Ваша подписка EIFAVPN</b>\n\n'
                        'Отсканируйте QR-код в VPN-клиенте (Hiddify, v2rayN) '
                        'или скопируйте ссылку ниже.'
                    ),
                    'parse_mode': 'HTML',
                },
                files={'photo': ('qr.png', qr_buf, 'image/png')},
                timeout=15,
            )
        except Exception as e:
            logging.warning(f'Failed to send QR photo for user {user.id}: {e}')

    # Always send text with the link (copyable)
    requests.post(
        f'https://api.telegram.org/bot{bot_token}/sendMessage',
        json={
            'chat_id': chat_id,
            'text': f'<code>{sub_url}</code>',
            'parse_mode': 'HTML',
        },
        timeout=10,
    )
