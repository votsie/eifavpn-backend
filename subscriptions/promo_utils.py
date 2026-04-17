"""Promo code validation and price calculation.

Two entry points used by subscriptions/views.py:

- validate_promo_for_user(user, code, plan=None, period=None) -> (PromoCode|None, error_str|None)
- calculate_promo_price(promo, plan, period, has_referral) -> dict

Works against the PromoCode + PromoCodeUsage models in accounts.models.
"""

from django.utils import timezone

from .plans import get_price

try:
    from accounts.models import PromoCode, PromoCodeUsage
except ImportError:  # pragma: no cover — model might not exist in some deployments
    PromoCode = None
    PromoCodeUsage = None


def validate_promo_for_user(user, code, plan=None, period=None):
    """Return (promo, None) if the promo is usable by this user in this context, else (None, error_str).

    Checks, in order:
      1. Models are installed.
      2. Code is non-empty and resolves (case-insensitive) to an active PromoCode.
      3. `valid_until` has not passed.
      4. Global `max_uses` cap (if > 0) is not exceeded.
      5. Per-user usage count is below `per_user_limit`.
      6. If `plan` is given and the promo restricts to a plan, they match.
      7. If `period` is given and the promo restricts to periods, the period is allowed.
    """
    if PromoCode is None or PromoCodeUsage is None:
        return None, 'Промокоды не доступны'

    if not code:
        return None, 'Введите промокод'

    code = code.strip().upper()
    try:
        promo = PromoCode.objects.get(code__iexact=code, is_active=True)
    except PromoCode.DoesNotExist:
        return None, 'Промокод не найден'

    if promo.valid_until and promo.valid_until < timezone.now():
        return None, 'Срок действия промокода истёк'

    if promo.max_uses > 0 and promo.times_used >= promo.max_uses:
        return None, 'Промокод исчерпан'

    if user is not None and promo.per_user_limit > 0:
        used_by_user = PromoCodeUsage.objects.filter(promo=promo, user=user).count()
        if used_by_user >= promo.per_user_limit:
            return None, 'Вы уже использовали этот промокод'

    if plan and promo.plan and promo.plan != plan:
        return None, f'Промокод действителен только для тарифа {promo.plan}'

    if period and promo.allowed_periods:
        try:
            period_int = int(period)
        except (TypeError, ValueError):
            return None, 'Неверный период'
        if period_int not in promo.allowed_periods:
            allowed = ', '.join(str(p) for p in promo.allowed_periods)
            return None, f'Промокод действителен только для периодов: {allowed} мес'

    return promo, None


def calculate_promo_price(promo, plan, period, has_referral):
    """Given a validated promo, return the price breakdown as a dict.

    Returns keys: base_price, referral_discount, after_referral, promo_discount,
    bonus_days, final_price, original_monthly.
    """
    base_price = get_price(plan, period)
    referral_discount = round(base_price * 0.10) if has_referral else 0
    after_referral = base_price - referral_discount

    promo_discount = 0
    bonus_days = 0

    if promo is not None:
        if promo.promo_type == 'percent':
            promo_discount = round(after_referral * promo.value / 100)
        elif promo.promo_type == 'days':
            bonus_days = promo.value
        # 'gift' type doesn't affect purchase price (it's activated without purchase).

    final_price = max(after_referral - promo_discount, 1)
    original_monthly = get_price(plan, 1)

    return {
        'base_price': base_price,
        'referral_discount': referral_discount,
        'after_referral': after_referral,
        'promo_discount': promo_discount,
        'bonus_days': bonus_days,
        'final_price': final_price,
        'original_monthly': original_monthly,
    }
