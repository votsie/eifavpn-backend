"""Shared invoice creation functions for all payment methods."""

import json
import requests
from django.conf import settings
from .plans import PLANS

try:
    from .exchange_rates import rub_to_crypto, rub_to_stars
except ImportError:
    rub_to_crypto = None
    rub_to_stars = None


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
    """Create CryptoPay invoice in specific cryptocurrency."""
    token = settings.CRYPTOPAY_TOKEN

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
    """Create Wata H2H payment link."""
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
