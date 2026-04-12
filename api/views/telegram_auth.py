import hashlib
import hmac
import time
import requests
from django.conf import settings
from django.http import HttpResponseRedirect


def telegram_login(request):
    """Redirect to Telegram Login Widget page (hosted on our site)."""
    return HttpResponseRedirect(f'{settings.APP_URL}/cabinet/login?show_telegram=1')


def telegram_callback(request):
    """Handle callback from Telegram Login Widget (data-auth-url redirect)."""
    app_url = settings.APP_URL
    bot_token = settings.TELEGRAM_BOT_TOKEN
    params = request.GET.dict()

    tg_id = params.get('id')
    tg_hash = params.get('hash')

    if not tg_id or not tg_hash:
        return HttpResponseRedirect(f'{app_url}/cabinet/login?error=no_telegram_data')

    # Verify HMAC-SHA-256
    secret = hashlib.sha256(bot_token.encode()).digest()
    check_string = '\n'.join(
        f'{k}={v}' for k, v in sorted(params.items()) if k != 'hash'
    )
    computed = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()

    if computed != tg_hash:
        return HttpResponseRedirect(f'{app_url}/cabinet/login?error=telegram_invalid')

    # Check freshness (5 minutes)
    auth_date = int(params.get('auth_date', 0))
    if time.time() - auth_date > 300:
        return HttpResponseRedirect(f'{app_url}/cabinet/login?error=telegram_expired')

    try:
        # Look up in Remnawave by Telegram ID
        rmn_resp = requests.get(
            f'{settings.REMNAWAVE_API_URL}/users/by-telegram-id/{tg_id}',
            headers={
                'Authorization': f'Bearer {settings.REMNAWAVE_BEARER_TOKEN}',
                'Content-Type': 'application/json',
            },
            timeout=10,
        )

        if not rmn_resp.ok:
            username = params.get('username', tg_id)
            return HttpResponseRedirect(
                f'{app_url}/cabinet/login?error=not_found&telegram={username}'
            )

        data = rmn_resp.json()
        user = data.get('response', data)
        short_uuid = user.get('shortUuid')

        return HttpResponseRedirect(
            f'{app_url}/cabinet/login?auth=telegram&shortUuid={short_uuid}'
        )
    except Exception:
        return HttpResponseRedirect(f'{app_url}/cabinet/login?error=server')
