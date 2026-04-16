"""Admin API views for the EIFAVPN dashboard."""

import logging
from datetime import timedelta
from collections import defaultdict

import requests
from django.conf import settings
from django.db import connection
from django.db.models import (
    Count, Sum, Q, F, Value, CharField,
)
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User, Subscription, Referral

try:
    from accounts.models import PromoCode, PromoCodeUsage
except ImportError:
    PromoCode = None
    PromoCodeUsage = None

from subscriptions import remnawave

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def paginate_qs(queryset, request, default_page_size=20):
    """Simple offset pagination. Returns (page_items, meta_dict)."""
    try:
        page = max(int(request.query_params.get('page', 1)), 1)
    except (ValueError, TypeError):
        page = 1
    try:
        page_size = min(max(int(request.query_params.get('page_size', default_page_size)), 1), 100)
    except (ValueError, TypeError):
        page_size = default_page_size

    total = queryset.count()
    start = (page - 1) * page_size
    items = list(queryset[start:start + page_size])
    return items, {
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': max((total + page_size - 1) // page_size, 1),
    }


def serialize_user_short(u):
    return {
        'id': u.id,
        'email': u.email,
        'username': u.username,
        'telegram_id': u.telegram_id,
        'is_staff': u.is_staff,
        'is_active': u.is_active,
        'date_joined': u.date_joined.isoformat(),
        'used_trial': u.used_trial,
        'referral_code': u.referral_code,
        'avatar_url': u.avatar_url,
    }


def serialize_user_detail(u):
    data = serialize_user_short(u)
    data.update({
        'google_id': u.google_id,
        'remnawave_uuid': str(u.remnawave_uuid) if u.remnawave_uuid else None,
        'remnawave_short_uuid': u.remnawave_short_uuid,
        'subscription_url': u.subscription_url,
        'referred_by_id': u.referred_by_id,
        'referral_bonus_days': u.referral_bonus_days,
        'used_trial_upgrade': u.used_trial_upgrade,
        'email_verified': u.email_verified,
        'last_login': u.last_login.isoformat() if u.last_login else None,
    })
    return data


def serialize_subscription(s):
    return {
        'id': s.id,
        'user_id': s.user_id,
        'user_email': s.user.email if hasattr(s, '_user_cache') or s.user_id else '',
        'plan': s.plan,
        'period_months': s.period_months,
        'price_paid': str(s.price_paid),
        'payment_method': s.payment_method,
        'payment_id': s.payment_id,
        'status': s.status,
        'created_at': s.created_at.isoformat(),
        'expires_at': s.expires_at.isoformat(),
        'remnawave_uuid': str(s.remnawave_uuid) if s.remnawave_uuid else None,
    }


def serialize_referral(r):
    return {
        'id': r.id,
        'referrer_id': r.referrer_id,
        'referrer_email': r.referrer.email,
        'referred_id': r.referred_id,
        'referred_email': r.referred.email,
        'bonus_applied': r.bonus_applied,
        'created_at': r.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# 1. Dashboard Stats
# ---------------------------------------------------------------------------

class StatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        now = timezone.now()
        total_users = User.objects.count()
        active_subs = Subscription.objects.filter(status='paid', expires_at__gt=now).count()
        revenue = Subscription.objects.filter(status='paid').aggregate(
            total=Sum('price_paid')
        )['total'] or 0
        trial_count = User.objects.filter(used_trial=True).count()
        referral_count = Referral.objects.count()

        return Response({
            'total_users': total_users,
            'active_subscriptions': active_subs,
            'total_revenue': str(revenue),
            'trial_count': trial_count,
            'referral_count': referral_count,
        })


# ---------------------------------------------------------------------------
# 2. Registration Chart
# ---------------------------------------------------------------------------

class RegistrationChartView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        qs = (
            User.objects
            .filter(date_joined__gte=since)
            .annotate(date=TruncDate('date_joined'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        # Fill in zero-days
        data_map = {str(row['date']): row['count'] for row in qs}
        result = []
        for i in range(days):
            d = (since + timedelta(days=i)).date()
            result.append({'date': str(d), 'count': data_map.get(str(d), 0)})
        return Response(result)


# ---------------------------------------------------------------------------
# 3. Revenue Chart
# ---------------------------------------------------------------------------

class RevenueChartView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        qs = (
            Subscription.objects
            .filter(status='paid', created_at__gte=since)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(total=Sum('price_paid'), count=Count('id'))
            .order_by('date')
        )
        data_map = {str(row['date']): {'total': str(row['total']), 'count': row['count']} for row in qs}
        result = []
        for i in range(days):
            d = (since + timedelta(days=i)).date()
            ds = str(d)
            result.append({
                'date': ds,
                'total': data_map.get(ds, {}).get('total', '0'),
                'count': data_map.get(ds, {}).get('count', 0),
            })
        return Response(result)


# ---------------------------------------------------------------------------
# 4. Activity Feed
# ---------------------------------------------------------------------------

class ActivityFeedView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        limit = min(int(request.query_params.get('limit', 20)), 50)
        events = []

        # Recent registrations
        for u in User.objects.order_by('-date_joined')[:limit]:
            events.append({
                'type': 'registration',
                'timestamp': u.date_joined.isoformat(),
                'description': f'New user: {u.email}',
                'user_id': u.id,
            })

        # Recent paid subscriptions
        for s in Subscription.objects.filter(status='paid').select_related('user').order_by('-created_at')[:limit]:
            events.append({
                'type': 'payment',
                'timestamp': s.created_at.isoformat(),
                'description': f'{s.user.email} paid {s.price_paid} RUB ({s.plan}/{s.payment_method})',
                'user_id': s.user_id,
            })

        # Recent trials
        for s in Subscription.objects.filter(payment_method='trial').select_related('user').order_by('-created_at')[:limit]:
            events.append({
                'type': 'trial',
                'timestamp': s.created_at.isoformat(),
                'description': f'{s.user.email} activated trial',
                'user_id': s.user_id,
            })

        events.sort(key=lambda e: e['timestamp'], reverse=True)
        return Response(events[:limit])


# ---------------------------------------------------------------------------
# 5. Expiring Subscriptions
# ---------------------------------------------------------------------------

class ExpiringSubsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        now = timezone.now()
        week = now + timedelta(days=7)
        qs = (
            Subscription.objects
            .filter(status='paid', expires_at__gt=now, expires_at__lte=week)
            .select_related('user')
            .order_by('expires_at')
        )
        result = []
        for s in qs[:50]:
            result.append({
                'subscription_id': s.id,
                'user_id': s.user_id,
                'user_email': s.user.email,
                'plan': s.plan,
                'expires_at': s.expires_at.isoformat(),
                'days_left': (s.expires_at - now).days,
            })
        return Response(result)


# ---------------------------------------------------------------------------
# 6. User List
# ---------------------------------------------------------------------------

class UserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = User.objects.all()

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(email__icontains=search) |
                Q(username__icontains=search) |
                Q(telegram_id__icontains=search) |
                Q(referral_code__icontains=search)
            )

        ordering = request.query_params.get('ordering', '-date_joined')
        allowed_ordering = [
            'date_joined', '-date_joined', 'email', '-email',
            'last_login', '-last_login', 'id', '-id',
        ]
        if ordering in allowed_ordering:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by('-date_joined')

        items, meta = paginate_qs(qs, request)
        return Response({
            'results': [serialize_user_short(u) for u in items],
            **meta,
        })


# ---------------------------------------------------------------------------
# 7-8. User Detail / Update
# ---------------------------------------------------------------------------

class UserDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        data = serialize_user_detail(user)
        # Attach subscription summary
        active_sub = user.subscriptions.filter(status='paid', expires_at__gt=timezone.now()).first()
        data['active_subscription'] = serialize_subscription(active_sub) if active_sub else None
        data['total_paid'] = str(
            user.subscriptions.filter(status='paid').aggregate(t=Sum('price_paid'))['t'] or 0
        )
        data['subscription_count'] = user.subscriptions.count()
        return Response(data)

    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        allowed_fields = ['is_staff', 'is_active', 'email_verified', 'used_trial', 'used_trial_upgrade']
        updated = []
        for field in allowed_fields:
            if field in request.data:
                setattr(user, field, request.data[field])
                updated.append(field)

        if updated:
            user.save(update_fields=updated)
            _log_admin_action(request.user, 'update_user', {
                'target_user_id': pk,
                'fields': updated,
            })

        return Response(serialize_user_detail(user))


# ---------------------------------------------------------------------------
# 9. Extend User Subscription
# ---------------------------------------------------------------------------

class UserExtendView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        days = int(request.data.get('days', 0))
        if days < 1 or days > 365:
            return Response({'error': 'days must be between 1 and 365'}, status=400)

        if not user.remnawave_uuid:
            return Response({'error': 'User has no Remnawave subscription'}, status=400)

        try:
            result = remnawave.extend_subscription(user.remnawave_uuid, days)
        except Exception as e:
            logger.error(f'Admin extend failed for user {pk}: {e}')
            return Response({'error': f'Remnawave error: {str(e)}'}, status=500)

        _log_admin_action(request.user, 'extend_subscription', {
            'target_user_id': pk,
            'days': days,
        })

        return Response({
            'success': True,
            'days_added': days,
            'new_expire_at': result.get('expireAt'),
        })


# ---------------------------------------------------------------------------
# 10. User Timeline
# ---------------------------------------------------------------------------

class UserTimelineView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        events = []

        # Registration
        events.append({
            'type': 'registration',
            'timestamp': user.date_joined.isoformat(),
            'description': 'Account created',
        })

        # Subscriptions
        for s in user.subscriptions.all().order_by('created_at'):
            label = f'{s.plan} ({s.period_months}m)' if s.period_months else s.plan
            if s.payment_method == 'trial':
                events.append({
                    'type': 'trial',
                    'timestamp': s.created_at.isoformat(),
                    'description': f'Trial activated: {label}',
                })
            elif s.status == 'paid':
                events.append({
                    'type': 'payment',
                    'timestamp': s.created_at.isoformat(),
                    'description': f'Paid {s.price_paid} RUB via {s.payment_method}: {label}',
                })
            else:
                events.append({
                    'type': 'subscription',
                    'timestamp': s.created_at.isoformat(),
                    'description': f'Subscription {s.status}: {label}',
                })

        # Referrals made
        for r in Referral.objects.filter(referrer=user).select_related('referred'):
            events.append({
                'type': 'referral',
                'timestamp': r.created_at.isoformat(),
                'description': f'Referred {r.referred.email}',
            })

        # Was referred
        for r in Referral.objects.filter(referred=user).select_related('referrer'):
            events.append({
                'type': 'referral',
                'timestamp': r.created_at.isoformat(),
                'description': f'Was referred by {r.referrer.email}',
            })

        events.sort(key=lambda e: e['timestamp'])
        return Response(events)


# ---------------------------------------------------------------------------
# 11. User Remnawave Data
# ---------------------------------------------------------------------------

class UserRemnawaveView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        if not user.remnawave_uuid:
            return Response({'remnawave': None})

        try:
            data = remnawave.get_user_data(user.remnawave_uuid)
        except Exception as e:
            return Response({'error': f'Remnawave error: {str(e)}'}, status=502)

        return Response({'remnawave': data})


# ---------------------------------------------------------------------------
# 12. Subscription List
# ---------------------------------------------------------------------------

class SubscriptionListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = Subscription.objects.select_related('user').all()

        status = request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)

        plan = request.query_params.get('plan')
        if plan:
            qs = qs.filter(plan=plan)

        method = request.query_params.get('method')
        if method:
            qs = qs.filter(payment_method=method)

        qs = qs.order_by('-created_at')
        items, meta = paginate_qs(qs, request)
        return Response({
            'results': [serialize_subscription(s) for s in items],
            **meta,
        })


# ---------------------------------------------------------------------------
# 13. Manage Subscription
# ---------------------------------------------------------------------------

class SubscriptionManageView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            sub = Subscription.objects.select_related('user').get(pk=pk)
        except Subscription.DoesNotExist:
            return Response({'error': 'Subscription not found'}, status=404)

        action = request.data.get('action')  # cancel, extend, change_status

        if action == 'cancel':
            sub.status = 'cancelled'
            sub.save(update_fields=['status'])
            _log_admin_action(request.user, 'cancel_subscription', {'sub_id': pk})
            return Response({'success': True, 'status': 'cancelled'})

        elif action == 'extend':
            days = int(request.data.get('days', 0))
            if days < 1:
                return Response({'error': 'days must be >= 1'}, status=400)
            sub.expires_at = sub.expires_at + timedelta(days=days)
            sub.save(update_fields=['expires_at'])

            # Also extend in Remnawave if possible
            user = sub.user
            if user.remnawave_uuid:
                try:
                    remnawave.extend_subscription(user.remnawave_uuid, days)
                except Exception as e:
                    logger.warning(f'Remnawave extend failed for sub {pk}: {e}')

            _log_admin_action(request.user, 'extend_subscription', {
                'sub_id': pk, 'days': days,
            })
            return Response({
                'success': True,
                'new_expires_at': sub.expires_at.isoformat(),
            })

        elif action == 'change_status':
            new_status = request.data.get('status')
            if new_status not in dict(Subscription.STATUS_CHOICES):
                return Response({'error': 'Invalid status'}, status=400)
            sub.status = new_status
            sub.save(update_fields=['status'])
            _log_admin_action(request.user, 'change_sub_status', {
                'sub_id': pk, 'new_status': new_status,
            })
            return Response({'success': True, 'status': new_status})

        return Response({'error': 'Unknown action'}, status=400)


# ---------------------------------------------------------------------------
# 14. Payment List
# ---------------------------------------------------------------------------

class PaymentListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = Subscription.objects.filter(status='paid').select_related('user')

        method = request.query_params.get('method')
        if method:
            qs = qs.filter(payment_method=method)

        qs = qs.order_by('-created_at')
        items, meta = paginate_qs(qs, request)
        return Response({
            'results': [serialize_subscription(s) for s in items],
            **meta,
        })


# ---------------------------------------------------------------------------
# 15. Referral List
# ---------------------------------------------------------------------------

class ReferralListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = Referral.objects.select_related('referrer', 'referred').order_by('-created_at')
        items, meta = paginate_qs(qs, request)
        return Response({
            'results': [serialize_referral(r) for r in items],
            **meta,
        })


# ---------------------------------------------------------------------------
# 16. Cohort Analysis
# ---------------------------------------------------------------------------

class CohortAnalysisView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Weekly cohorts for the last 12 weeks: registered -> paid conversion."""
        weeks = int(request.query_params.get('weeks', 12))
        now = timezone.now()
        cohorts = []

        for w in range(weeks):
            start = now - timedelta(weeks=w + 1)
            end = now - timedelta(weeks=w)
            registered = User.objects.filter(date_joined__gte=start, date_joined__lt=end)
            reg_count = registered.count()
            if reg_count == 0:
                cohorts.append({
                    'week': str(start.date()),
                    'registered': 0,
                    'trial': 0,
                    'paid': 0,
                    'trial_rate': 0,
                    'paid_rate': 0,
                })
                continue

            reg_ids = list(registered.values_list('id', flat=True))
            trial_count = User.objects.filter(id__in=reg_ids, used_trial=True).count()
            paid_count = (
                Subscription.objects
                .filter(user_id__in=reg_ids, status='paid')
                .exclude(payment_method='trial')
                .values('user_id')
                .distinct()
                .count()
            )

            cohorts.append({
                'week': str(start.date()),
                'registered': reg_count,
                'trial': trial_count,
                'paid': paid_count,
                'trial_rate': round(trial_count / reg_count * 100, 1),
                'paid_rate': round(paid_count / reg_count * 100, 1),
            })

        cohorts.reverse()
        return Response(cohorts)


# ---------------------------------------------------------------------------
# 17. Funnel
# ---------------------------------------------------------------------------

class FunnelView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        total_registered = User.objects.count()
        total_trial = User.objects.filter(used_trial=True).count()
        total_paid = (
            Subscription.objects
            .filter(status='paid')
            .exclude(payment_method='trial')
            .values('user_id')
            .distinct()
            .count()
        )

        return Response({
            'registered': total_registered,
            'trial': total_trial,
            'paid': total_paid,
            'trial_rate': round(total_trial / max(total_registered, 1) * 100, 1),
            'paid_rate': round(total_paid / max(total_registered, 1) * 100, 1),
            'trial_to_paid_rate': round(total_paid / max(total_trial, 1) * 100, 1),
        })


# ---------------------------------------------------------------------------
# 18. Forecast
# ---------------------------------------------------------------------------

class ForecastView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Simple linear forecast based on last 30 days trends."""
        now = timezone.now()
        last_30 = now - timedelta(days=30)
        last_60 = now - timedelta(days=60)

        # Registrations
        regs_30 = User.objects.filter(date_joined__gte=last_30).count()
        regs_60 = User.objects.filter(date_joined__gte=last_60, date_joined__lt=last_30).count()

        # Revenue
        rev_30 = Subscription.objects.filter(
            status='paid', created_at__gte=last_30
        ).aggregate(t=Sum('price_paid'))['t'] or 0
        rev_60 = Subscription.objects.filter(
            status='paid', created_at__gte=last_60, created_at__lt=last_30
        ).aggregate(t=Sum('price_paid'))['t'] or 0

        def growth_rate(current, previous):
            if previous == 0:
                return 0
            return round((float(current) - float(previous)) / float(previous) * 100, 1)

        reg_growth = growth_rate(regs_30, regs_60)
        rev_growth = growth_rate(rev_30, rev_60)

        # Simple next-30-day forecast
        forecast_regs = max(round(regs_30 * (1 + reg_growth / 100)), 0)
        forecast_rev = max(round(float(rev_30) * (1 + rev_growth / 100)), 0)

        return Response({
            'period': '30d',
            'registrations': {
                'last_30d': regs_30,
                'prev_30d': regs_60,
                'growth_percent': reg_growth,
                'forecast_next_30d': forecast_regs,
            },
            'revenue': {
                'last_30d': str(rev_30),
                'prev_30d': str(rev_60),
                'growth_percent': rev_growth,
                'forecast_next_30d': str(forecast_rev),
            },
        })


# ---------------------------------------------------------------------------
# 19. Audit Log (in-memory, stored via Django's LogEntry or custom)
# ---------------------------------------------------------------------------

# We use a simple DB-backed approach via Django's admin LogEntry as a fallback,
# but since we want custom actions, we store in a lightweight cache/table.
# For now, use Django's admin log if available, otherwise return recent actions.

_audit_log = []  # In-memory for this process; for production, use a model or cache


def _log_admin_action(admin_user, action, details=None):
    """Append an admin action to the audit log."""
    _audit_log.append({
        'admin_id': admin_user.id,
        'admin_email': admin_user.email,
        'action': action,
        'details': details or {},
        'timestamp': timezone.now().isoformat(),
    })
    # Keep only last 500 entries in memory
    if len(_audit_log) > 500:
        _audit_log.pop(0)


class AuditLogView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            page = max(int(request.query_params.get('page', 1)), 1)
        except (ValueError, TypeError):
            page = 1
        page_size = 20
        start = (page - 1) * page_size
        end = start + page_size

        # Combine in-memory log with Django's admin log
        from django.contrib.admin.models import LogEntry
        django_entries = []
        for entry in LogEntry.objects.select_related('user').order_by('-action_time')[:200]:
            django_entries.append({
                'admin_id': entry.user_id,
                'admin_email': entry.user.email if entry.user else '',
                'action': entry.get_action_flag_display(),
                'details': {
                    'object_repr': entry.object_repr,
                    'change_message': entry.get_change_message(),
                },
                'timestamp': entry.action_time.isoformat(),
            })

        combined = sorted(
            _audit_log + django_entries,
            key=lambda x: x['timestamp'],
            reverse=True,
        )

        total = len(combined)
        return Response({
            'results': combined[start:end],
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': max((total + page_size - 1) // page_size, 1),
        })


# ---------------------------------------------------------------------------
# 20. System Health
# ---------------------------------------------------------------------------

class SystemHealthView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        health = {'status': 'ok', 'checks': {}}

        # Database
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            health['checks']['database'] = {'status': 'ok'}
        except Exception as e:
            health['checks']['database'] = {'status': 'error', 'detail': str(e)}
            health['status'] = 'degraded'

        # Remnawave API
        try:
            resp = requests.get(
                f'{settings.REMNAWAVE_API_URL}/users',
                headers={
                    'Authorization': f'Bearer {settings.REMNAWAVE_BEARER_TOKEN}',
                    'Content-Type': 'application/json',
                },
                timeout=5,
                params={'limit': 1},
            )
            if resp.ok:
                health['checks']['remnawave'] = {'status': 'ok'}
            else:
                health['checks']['remnawave'] = {
                    'status': 'error',
                    'detail': f'HTTP {resp.status_code}',
                }
                health['status'] = 'degraded'
        except Exception as e:
            health['checks']['remnawave'] = {'status': 'error', 'detail': str(e)}
            health['status'] = 'degraded'

        # Email (just check settings are configured)
        if settings.EMAIL_HOST and settings.EMAIL_HOST != 'localhost':
            health['checks']['email'] = {'status': 'ok', 'host': settings.EMAIL_HOST}
        else:
            health['checks']['email'] = {
                'status': 'warning',
                'detail': 'Using localhost SMTP',
            }

        return Response(health)


# ---------------------------------------------------------------------------
# 21-22. Settings
# ---------------------------------------------------------------------------

# Simple key-value store in memory (in production, use a model or cache)
_app_settings = {}


class SettingsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response({
            'REMNAWAVE_API_URL': settings.REMNAWAVE_API_URL,
            'APP_URL': settings.APP_URL,
            'EMAIL_HOST': settings.EMAIL_HOST,
            'TELEGRAM_BOT_TOKEN': '***' if settings.TELEGRAM_BOT_TOKEN else '',
            'CRYPTOPAY_TOKEN': '***' if settings.CRYPTOPAY_TOKEN else '',
            'WATA_TOKEN': '***' if settings.WATA_TOKEN else '',
            **_app_settings,
        })

    def patch(self, request):
        allowed = ['maintenance_mode', 'trial_enabled', 'registration_enabled', 'motd']
        updated = []
        for key in allowed:
            if key in request.data:
                _app_settings[key] = request.data[key]
                updated.append(key)

        if updated:
            _log_admin_action(request.user, 'update_settings', {'keys': updated})

        return Response({**self._base_settings(), **_app_settings})

    def _base_settings(self):
        return {
            'REMNAWAVE_API_URL': settings.REMNAWAVE_API_URL,
            'APP_URL': settings.APP_URL,
            'EMAIL_HOST': settings.EMAIL_HOST,
            'TELEGRAM_BOT_TOKEN': '***' if settings.TELEGRAM_BOT_TOKEN else '',
            'CRYPTOPAY_TOKEN': '***' if settings.CRYPTOPAY_TOKEN else '',
            'WATA_TOKEN': '***' if settings.WATA_TOKEN else '',
        }


# ---------------------------------------------------------------------------
# 23. Global Search
# ---------------------------------------------------------------------------

class GlobalSearchView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        if not q or len(q) < 2:
            return Response({'users': [], 'subscriptions': [], 'promos': []})

        users = User.objects.filter(
            Q(email__icontains=q) |
            Q(username__icontains=q) |
            Q(referral_code__icontains=q)
        )[:10]

        subs = Subscription.objects.filter(
            Q(user__email__icontains=q) |
            Q(payment_id__icontains=q)
        ).select_related('user')[:10]

        promos = []
        if PromoCode is not None:
            try:
                promos_qs = PromoCode.objects.filter(code__icontains=q)[:10]
                promos = [
                    {
                        'id': p.id,
                        'code': p.code,
                        'promo_type': p.promo_type,
                        'value': p.value,
                        'is_active': p.is_active,
                    }
                    for p in promos_qs
                ]
            except Exception:
                pass

        return Response({
            'users': [serialize_user_short(u) for u in users],
            'subscriptions': [serialize_subscription(s) for s in subs],
            'promos': promos,
        })


# ---------------------------------------------------------------------------
# 24-25. Notifications
# ---------------------------------------------------------------------------

class SendNotificationView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        user_ids = request.data.get('user_ids', [])
        message = request.data.get('message', '').strip()

        if not message:
            return Response({'error': 'Message is required'}, status=400)
        if not user_ids:
            return Response({'error': 'user_ids is required'}, status=400)

        bot_token = settings.TELEGRAM_BOT_TOKEN
        if not bot_token:
            return Response({'error': 'TELEGRAM_BOT_TOKEN not configured'}, status=500)

        users = User.objects.filter(id__in=user_ids, telegram_id__isnull=False)
        sent = 0
        failed = 0

        for user in users:
            try:
                resp = requests.post(
                    f'https://api.telegram.org/bot{bot_token}/sendMessage',
                    json={
                        'chat_id': user.telegram_id,
                        'text': message,
                        'parse_mode': 'HTML',
                    },
                    timeout=10,
                )
                if resp.ok:
                    sent += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

        _log_admin_action(request.user, 'send_notification', {
            'user_ids': user_ids,
            'message_preview': message[:100],
            'sent': sent,
            'failed': failed,
        })

        # Store in notification history
        _notification_history.append({
            'admin_id': request.user.id,
            'admin_email': request.user.email,
            'user_ids': user_ids,
            'message': message,
            'sent': sent,
            'failed': failed,
            'timestamp': timezone.now().isoformat(),
        })

        return Response({'sent': sent, 'failed': failed})


_notification_history = []


class NotificationHistoryView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            page = max(int(request.query_params.get('page', 1)), 1)
        except (ValueError, TypeError):
            page = 1
        page_size = 20
        start = (page - 1) * page_size
        end = start + page_size

        history = sorted(_notification_history, key=lambda x: x['timestamp'], reverse=True)
        total = len(history)
        return Response({
            'results': history[start:end],
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': max((total + page_size - 1) // page_size, 1),
        })


# ---------------------------------------------------------------------------
# 26-29. Promo Codes
# ---------------------------------------------------------------------------

class PromoListCreateView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        if PromoCode is None:
            return Response({'results': [], 'page': 1, 'page_size': 20, 'total': 0, 'total_pages': 1})

        qs = PromoCode.objects.all().order_by('-id')
        items, meta = paginate_qs(qs, request)
        return Response({
            'results': [self._serialize(p) for p in items],
            **meta,
        })

    def post(self, request):
        if PromoCode is None:
            return Response({'error': 'PromoCode model not available'}, status=501)

        data = request.data
        try:
            promo = PromoCode.objects.create(
                code=data['code'].strip().upper(),
                promo_type=data.get('promo_type', 'percent'),
                value=int(data.get('value', 0)),
                description=data.get('description', ''),
                plan=data.get('plan', ''),
                allowed_periods=data.get('allowed_periods', []),
                max_uses=int(data.get('max_uses', 0)),
                is_active=data.get('is_active', True),
                valid_until=data.get('valid_until') or None,
            )
        except Exception as e:
            return Response({'error': str(e)}, status=400)

        _log_admin_action(request.user, 'create_promo', {'code': promo.code})
        return Response(self._serialize(promo), status=201)

    @staticmethod
    def _serialize(p):
        data = {
            'id': p.id,
            'code': p.code,
            'promo_type': p.promo_type,
            'value': p.value,
            'description': p.description,
            'is_active': p.is_active,
            'times_used': p.times_used,
            'max_uses': p.max_uses,
        }
        if hasattr(p, 'plan'):
            data['plan'] = p.plan
        if hasattr(p, 'allowed_periods'):
            data['allowed_periods'] = p.allowed_periods
        if hasattr(p, 'valid_until'):
            data['valid_until'] = p.valid_until.isoformat() if p.valid_until else None
        return data


class PromoDetailView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        if PromoCode is None:
            return Response({'error': 'PromoCode model not available'}, status=501)

        try:
            promo = PromoCode.objects.get(pk=pk)
        except PromoCode.DoesNotExist:
            return Response({'error': 'Promo not found'}, status=404)

        allowed_fields = [
            'code', 'promo_type', 'value', 'description', 'plan',
            'allowed_periods', 'max_uses', 'is_active', 'valid_until',
        ]
        updated = []
        for field in allowed_fields:
            if field in request.data:
                val = request.data[field]
                if field == 'code':
                    val = val.strip().upper()
                if field in ('value', 'max_uses'):
                    val = int(val)
                if field == 'valid_until' and val == '':
                    val = None
                setattr(promo, field, val)
                updated.append(field)

        if updated:
            promo.save(update_fields=updated)
            _log_admin_action(request.user, 'update_promo', {
                'promo_id': pk, 'fields': updated,
            })

        return Response(PromoListCreateView._serialize(promo))

    def delete(self, request, pk):
        if PromoCode is None:
            return Response({'error': 'PromoCode model not available'}, status=501)

        try:
            promo = PromoCode.objects.get(pk=pk)
        except PromoCode.DoesNotExist:
            return Response({'error': 'Promo not found'}, status=404)

        code = promo.code
        promo.delete()
        _log_admin_action(request.user, 'delete_promo', {'code': code})
        return Response({'success': True})


# ---------------------------------------------------------------------------
# 30. Bulk Extend
# ---------------------------------------------------------------------------

class BulkExtendView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        user_ids = request.data.get('user_ids', [])
        days = int(request.data.get('days', 0))

        if not user_ids:
            return Response({'error': 'user_ids is required'}, status=400)
        if days < 1 or days > 365:
            return Response({'error': 'days must be between 1 and 365'}, status=400)

        users = User.objects.filter(id__in=user_ids, remnawave_uuid__isnull=False)
        success = 0
        failed = 0
        errors = []

        for user in users:
            try:
                remnawave.extend_subscription(user.remnawave_uuid, days)
                success += 1
            except Exception as e:
                failed += 1
                errors.append({'user_id': user.id, 'error': str(e)})

        _log_admin_action(request.user, 'bulk_extend', {
            'user_ids': user_ids,
            'days': days,
            'success': success,
            'failed': failed,
        })

        return Response({
            'success': success,
            'failed': failed,
            'errors': errors,
        })
