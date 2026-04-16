"""Exchange rate fetching and conversion for payment methods."""

import logging
import time
import requests

logger = logging.getLogger(__name__)

# Cache rates for 5 minutes
_rate_cache = {'rates': {}, 'timestamp': 0, 'star_price': 0}
CACHE_TTL = 300  # 5 minutes


def get_rates():
    """Get current crypto exchange rates (USDT, TON, BTC in RUB).

    Sources: CoinGecko API (free, no key required).
    Returns dict: {USDT: float, TON: float, BTC: float, source: str}
    """
    now = time.time()
    if now - _rate_cache['timestamp'] < CACHE_TTL and _rate_cache['rates']:
        return _rate_cache['rates']

    try:
        resp = requests.get(
            'https://api.coingecko.com/api/v3/simple/price',
            params={
                'ids': 'tether,the-open-network,bitcoin',
                'vs_currencies': 'rub',
            },
            timeout=10,
        )
        data = resp.json()
        rates = {
            'USDT': data.get('tether', {}).get('rub', 0),
            'TON': data.get('the-open-network', {}).get('rub', 0),
            'BTC': data.get('bitcoin', {}).get('rub', 0),
            'source': 'coingecko',
        }
        _rate_cache['rates'] = rates
        _rate_cache['timestamp'] = now
        return rates
    except Exception as e:
        logger.warning(f'Failed to fetch exchange rates: {e}')
        # Return cached or fallback
        if _rate_cache['rates']:
            return _rate_cache['rates']
        return {
            'USDT': 95.0,
            'TON': 250.0,
            'BTC': 9000000.0,
            'source': 'fallback',
        }


def rub_to_crypto(amount_rub, asset='USDT'):
    """Convert RUB amount to crypto with 3% markup."""
    rates = get_rates()
    rate = rates.get(asset, 0)
    if rate <= 0:
        return 0
    crypto_amount = (float(amount_rub) * 1.03) / rate
    if asset == 'BTC':
        return round(crypto_amount, 6)
    return round(crypto_amount, 2)


def rub_to_stars(amount_rub):
    """Convert RUB to Telegram Stars.

    Stars pricing: 50 stars ≈ $0.75
    So 1 star ≈ $0.015 ≈ 0.015 * USDT_RUB rate
    Plus ~15% Telegram markup.
    """
    star_price = get_star_price_rub()
    if star_price <= 0:
        return max(int(amount_rub), 1)
    stars = (float(amount_rub) / star_price) * 1.15
    return max(int(stars) + 1, 1)  # Round up, minimum 1


def get_star_price_rub():
    """Get the price of 1 Telegram Star in RUB."""
    rates = get_rates()
    usdt_rub = rates.get('USDT', 95.0)
    # 50 stars = $0.75, so 1 star = $0.015
    star_usd = 0.015
    return round(star_usd * usdt_rub, 2)
