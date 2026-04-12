"""Remnawave API client for creating/managing VPN subscriptions."""

import requests
from django.conf import settings
from datetime import datetime, timedelta, timezone


def create_subscription(user, plan, period_months=0, days=None):
    """Create a NEW VPN subscription in Remnawave."""
    from .plans import PLANS

    config = PLANS[plan]
    if days:
        expire_at = datetime.now(timezone.utc) + timedelta(days=days)
    else:
        expire_at = datetime.now(timezone.utc) + timedelta(days=period_months * 30)

    payload = {
        'username': f'eifa_{user.id}_{plan}',
        'expireAt': expire_at.isoformat(),
        'trafficLimitBytes': config['traffic_bytes'],
        'trafficLimitStrategy': config.get('traffic_strategy', 'MONTH'),
        'hwidDeviceLimit': config['devices'],
        'tag': f'EIFA_{user.id}',
        'description': f'EIFAVPN {config["name"]} - {user.email}',
        'activeInternalSquadUuids': [config['squad_uuid']],
    }

    if user.email and not user.email.startswith('tg_'):
        payload['email'] = user.email
    if user.telegram_id:
        payload['telegramId'] = user.telegram_id

    resp = requests.post(
        f'{settings.REMNAWAVE_API_URL}/users',
        json=payload,
        headers=_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get('response', data)


def update_subscription(remnawave_uuid, plan, period_months=0, days=None):
    """Update EXISTING subscription: change plan (squad, traffic, devices, expiry)."""
    from .plans import PLANS

    config = PLANS[plan]
    if days:
        expire_at = datetime.now(timezone.utc) + timedelta(days=days)
    else:
        expire_at = datetime.now(timezone.utc) + timedelta(days=period_months * 30)

    # First extend expiry from current date (not from current expiry)
    payload = {
        'uuid': str(remnawave_uuid),
        'expireAt': expire_at.isoformat(),
        'status': 'ACTIVE',
        'trafficLimitBytes': config['traffic_bytes'],
        'trafficLimitStrategy': config.get('traffic_strategy', 'MONTH'),
        'hwidDeviceLimit': config['devices'],
        'activeInternalSquadUuids': [config['squad_uuid']],
    }

    resp = requests.patch(
        f'{settings.REMNAWAVE_API_URL}/users',
        json=payload,
        headers=_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get('response', data)


def extend_subscription(remnawave_uuid, days):
    """Extend existing subscription by N days (keep current plan settings)."""
    # Get current expiry
    resp = requests.get(
        f'{settings.REMNAWAVE_API_URL}/users/{remnawave_uuid}',
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    user_data = resp.json().get('response', resp.json())

    current_expiry = datetime.fromisoformat(user_data['expireAt'].replace('Z', '+00:00'))
    new_expiry = max(current_expiry, datetime.now(timezone.utc)) + timedelta(days=days)

    resp = requests.patch(
        f'{settings.REMNAWAVE_API_URL}/users',
        json={
            'uuid': str(remnawave_uuid),
            'expireAt': new_expiry.isoformat(),
            'status': 'ACTIVE',
        },
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get('response', resp.json())


def get_user_data(remnawave_uuid):
    """Get user data from Remnawave including traffic stats."""
    resp = requests.get(
        f'{settings.REMNAWAVE_API_URL}/users/{remnawave_uuid}',
        headers=_headers(),
        timeout=10,
    )
    if resp.ok:
        data = resp.json()
        return data.get('response', data)
    return None


def _headers():
    return {
        'Authorization': f'Bearer {settings.REMNAWAVE_BEARER_TOKEN}',
        'Content-Type': 'application/json',
    }
