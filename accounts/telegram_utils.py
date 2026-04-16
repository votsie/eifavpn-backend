"""Shared Telegram authentication utilities."""

import hashlib
import hmac as hmac_mod
import time

from django.conf import settings


def verify_widget_data(widget_data):
    """Verify Telegram Login Widget hash and return telegram_id + first_name.

    Returns (telegram_id: int, first_name: str) on success.
    Raises ValueError on any validation failure.
    """
    if not isinstance(widget_data, dict) or 'hash' not in widget_data or 'id' not in widget_data:
        raise ValueError('Invalid widget data')

    received_hash = widget_data['hash']
    if not isinstance(received_hash, str):
        raise ValueError('Invalid widget data')

    auth_date = int(widget_data.get('auth_date', 0))
    if time.time() - auth_date > 86400 or auth_date < 0:
        raise ValueError('Widget auth expired')

    check_fields = {k: str(v) for k, v in widget_data.items() if k != 'hash' and v is not None}
    data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(check_fields.items()))

    secret_key = hashlib.sha256(settings.TELEGRAM_BOT_TOKEN.encode()).digest()
    computed_hash = hmac_mod.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac_mod.compare_digest(computed_hash, received_hash):
        raise ValueError('Invalid widget hash')

    return int(widget_data['id']), str(widget_data.get('first_name', ''))
