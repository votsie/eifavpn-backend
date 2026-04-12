"""Pricing and plan configuration."""

PLANS = {
    'standard': {
        'name': 'Standard',
        'servers': 7,
        'devices': 3,
        'traffic_bytes': 107374182400,  # 100 GB
        'adblock': False,
        'p2p': False,
        'squad_uuid': None,  # Set in .env: SQUAD_STANDARD_UUID
    },
    'pro': {
        'name': 'Pro',
        'servers': 10,
        'devices': 4,
        'traffic_bytes': 0,  # unlimited
        'adblock': True,
        'p2p': False,
        'squad_uuid': None,  # Set in .env: SQUAD_PRO_UUID
    },
    'max': {
        'name': 'Max',
        'servers': 14,
        'devices': 6,
        'traffic_bytes': 0,  # unlimited
        'adblock': True,
        'p2p': True,
        'squad_uuid': None,  # Set in .env: SQUAD_MAX_UUID
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
