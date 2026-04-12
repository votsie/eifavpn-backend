"""Remnawave API client for creating/managing VPN subscriptions."""

import requests
from django.conf import settings
from datetime import datetime, timedelta, timezone
import os


def get_squad_uuid(plan):
    """Get squad UUID for plan from environment."""
    key = f'SQUAD_{plan.upper()}_UUID'
    return os.environ.get(key, settings.REMNAWAVE_DEFAULT_SQUAD)


def create_subscription(user, plan, period_months):
    """Create a new VPN subscription in Remnawave."""
    from .plans import PLANS

    config = PLANS[plan]
    expire_at = datetime.now(timezone.utc) + timedelta(days=period_months * 30)
    squad_uuid = get_squad_uuid(plan)

    payload = {
        'username': f'eifa_{user.id}_{plan}',
        'expireAt': expire_at.isoformat(),
        'trafficLimitBytes': config['traffic_bytes'],
        'trafficLimitStrategy': 'MONTH',
        'hwidDeviceLimit': config['devices'],
        'tag': f'EIFA_{user.id}',
        'description': f'EIFAVPN {config["name"]} - {user.email}',
    }

    if user.email and not user.email.startswith('tg_'):
        payload['email'] = user.email
    if user.telegram_id:
        payload['telegramId'] = user.telegram_id
    if squad_uuid:
        payload['activeInternalSquadUuids'] = [squad_uuid]

    resp = requests.post(
        f'{settings.REMNAWAVE_API_URL}/users',
        json=payload,
        headers={
            'Authorization': f'Bearer {settings.REMNAWAVE_BEARER_TOKEN}',
            'Content-Type': 'application/json',
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get('response', data)


def extend_subscription(remnawave_uuid, days):
    """Extend existing subscription by N days."""
    # First get current expiry
    resp = requests.get(
        f'{settings.REMNAWAVE_API_URL}/users/{remnawave_uuid}',
        headers={
            'Authorization': f'Bearer {settings.REMNAWAVE_BEARER_TOKEN}',
            'Content-Type': 'application/json',
        },
        timeout=10,
    )
    resp.raise_for_status()
    user_data = resp.json().get('response', resp.json())

    current_expiry = datetime.fromisoformat(user_data['expireAt'].replace('Z', '+00:00'))
    new_expiry = max(current_expiry, datetime.now(timezone.utc)) + timedelta(days=days)

    # Update expiry
    resp = requests.patch(
        f'{settings.REMNAWAVE_API_URL}/users',
        json={
            'uuid': str(remnawave_uuid),
            'expireAt': new_expiry.isoformat(),
            'status': 'ACTIVE',
        },
        headers={
            'Authorization': f'Bearer {settings.REMNAWAVE_BEARER_TOKEN}',
            'Content-Type': 'application/json',
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get('response', resp.json())
