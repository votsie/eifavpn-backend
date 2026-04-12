"""Pricing and plan configuration."""

# Squad UUIDs from Remnawave (hardcoded — stable identifiers)
SQUAD_UUIDS = {
    'standard': 'b88b61e7-eb76-49b4-878f-c53b3e078b37',
    'pro': 'd4f1b004-43a2-43bb-b429-bbd3a220de4a',
    'max': '67729b5d-e951-488a-bb85-f813b1532919',
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
