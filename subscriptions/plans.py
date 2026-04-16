"""Pricing and plan configuration."""

# Use Default-Squad for all plans (has all hosts configured)
# Plan differences enforced via traffic/devices, not squads
DEFAULT_SQUAD = '38d5757f-a45a-4144-b4b3-fd3f5facb5dd'

SQUAD_UUIDS = {
    'standard': DEFAULT_SQUAD,
    'pro': DEFAULT_SQUAD,
    'max': DEFAULT_SQUAD,
}

PLANS = {
    'standard': {
        'name': 'Standard',
        'servers': 7,
        'devices': 3,
        'traffic_bytes': 1099511627776,  # 1 TB
        'traffic_strategy': 'MONTH',
        'adblock': False,
        'p2p': False,
        'squad_uuid': SQUAD_UUIDS['standard'],
    },
    'pro': {
        'name': 'Pro',
        'servers': 10,
        'devices': 4,
        'traffic_bytes': 0,  # unlimited
        'traffic_strategy': 'NO_RESET',
        'adblock': True,
        'p2p': False,
        'squad_uuid': SQUAD_UUIDS['pro'],
    },
    'max': {
        'name': 'Max',
        'servers': 14,
        'devices': 6,
        'traffic_bytes': 0,  # unlimited
        'traffic_strategy': 'NO_RESET',
        'adblock': True,
        'p2p': True,
        'squad_uuid': SQUAD_UUIDS['max'],
    },
}

# Per-month prices (RUB) after discount
PRICING = {
    'standard': {1: 69, 3: 59, 6: 55, 12: 45},
    'pro': {1: 99, 3: 89, 6: 79, 12: 65},
    'max': {1: 149, 3: 129, 6: 119, 12: 99},
}

REFERRAL_DISCOUNT_PERCENT = 10
REFERRAL_BONUS_DAYS = 7


def get_price(plan, period):
    """Get total price for plan + period."""
    per_month = PRICING.get(plan, {}).get(period)
    if per_month is None:
        raise ValueError(f'Invalid plan={plan} or period={period}')
    return per_month * period


def get_price_with_referral(plan, period):
    """Get discounted price for referred user."""
    total = get_price(plan, period)
    discount = total * REFERRAL_DISCOUNT_PERCENT / 100
    return round(total - discount)


# Plan tier ordering for upgrade/downgrade detection
PLAN_TIERS = {'standard': 1, 'pro': 2, 'max': 3}


def get_upgrade_price(current_sub, new_plan, new_period):
    """Calculate pro-rata upgrade/downgrade cost.

    Args:
        current_sub: active Subscription object
        new_plan: target plan id
        new_period: target period in months

    Returns:
        dict with: charge_amount (>0 = pay, 0 = free), credit_days (for downgrade),
        is_upgrade (bool), new_total, current_credit
    """
    from django.utils import timezone

    now = timezone.now()
    current_expires = current_sub.expires_at

    # Remaining days on current plan
    remaining_days = max((current_expires - now).days, 0)
    total_days = current_sub.period_months * 30 if current_sub.period_months > 0 else remaining_days

    # Credit from current plan (proportional refund)
    if total_days > 0 and float(current_sub.price_paid) > 0:
        daily_rate_current = float(current_sub.price_paid) / total_days
        current_credit = round(daily_rate_current * remaining_days)
    else:
        current_credit = 0

    # New plan cost
    new_total = get_price(new_plan, new_period)

    current_tier = PLAN_TIERS.get(current_sub.plan, 0)
    new_tier = PLAN_TIERS.get(new_plan, 0)
    is_upgrade = new_tier > current_tier or (new_tier == current_tier and new_period > current_sub.period_months)

    if is_upgrade:
        charge_amount = max(new_total - current_credit, 1)
        credit_days = 0
    else:
        # Downgrade: convert excess credit to bonus days
        if new_total > 0:
            new_daily_rate = new_total / (new_period * 30)
            credit_days = round((current_credit - new_total) / new_daily_rate) if current_credit > new_total else 0
        else:
            credit_days = 0
        charge_amount = 0

    return {
        'charge_amount': charge_amount,
        'credit_days': credit_days,
        'is_upgrade': is_upgrade,
        'new_total': new_total,
        'current_credit': current_credit,
        'remaining_days': remaining_days,
    }
