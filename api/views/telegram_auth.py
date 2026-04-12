import requests
import jwt
from django.conf import settings
from django.http import HttpResponseRedirect
from urllib.parse import urlencode


# Telegram OAuth 2.0 / OpenID Connect endpoints
TELEGRAM_AUTH_URL = 'https://oauth.telegram.org/auth'
TELEGRAM_TOKEN_URL = 'https://oauth.telegram.org/token'
TELEGRAM_JWKS_URL = 'https://oauth.telegram.org/.well-known/jwks.json'

REMNAWAVE_API_URL = None  # loaded from settings at runtime


def telegram_login(request):
    """Step 1: Redirect user to Telegram OAuth authorization page."""
    bot_id = settings.TELEGRAM_BOT_ID
    redirect_uri = f'{settings.APP_URL}/api/auth/telegram/callback/'

    params = urlencode({
        'bot_id': bot_id,
        'scope': 'openid profile',
        'response_type': 'code',
        'redirect_uri': redirect_uri,
    })

    return HttpResponseRedirect(f'{TELEGRAM_AUTH_URL}?{params}')


def telegram_callback(request):
    """Step 2: Handle callback from Telegram OAuth, exchange code for token."""
    code = request.GET.get('code')
    app_url = settings.APP_URL
    redirect_uri = f'{app_url}/api/auth/telegram/callback/'

    if not code:
        return HttpResponseRedirect(f'{app_url}/cabinet/login?error=no_telegram_code')

    try:
        # Exchange authorization code for tokens
        token_resp = requests.post(TELEGRAM_TOKEN_URL, data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': settings.TELEGRAM_BOT_ID,
            'client_secret': settings.TELEGRAM_BOT_SECRET,
        }, timeout=10)

        if not token_resp.ok:
            return HttpResponseRedirect(f'{app_url}/cabinet/login?error=telegram_token')

        tokens = token_resp.json()
        id_token = tokens.get('id_token')

        if not id_token:
            return HttpResponseRedirect(f'{app_url}/cabinet/login?error=telegram_no_id_token')

        # Fetch JWKS and verify ID token
        jwks_resp = requests.get(TELEGRAM_JWKS_URL, timeout=10)
        jwks = jwks_resp.json()

        # Decode the ID token (verify signature with Telegram's public keys)
        # PyJWT with cryptography handles RS256 verification
        signing_key = jwt.PyJWKClient(TELEGRAM_JWKS_URL).get_signing_key_from_jwt(id_token)
        decoded = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=['RS256'],
            audience=str(settings.TELEGRAM_BOT_ID),
            issuer='https://oauth.telegram.org',
        )

        # Extract Telegram user ID from 'sub' claim
        telegram_id = decoded.get('sub')
        telegram_username = decoded.get('username', '')
        telegram_name = decoded.get('name', '')

        if not telegram_id:
            return HttpResponseRedirect(f'{app_url}/cabinet/login?error=telegram_no_id')

        # Look up user in Remnawave by Telegram ID
        rmn_resp = requests.get(
            f'{settings.REMNAWAVE_API_URL}/users/by-telegram-id/{telegram_id}',
            headers={
                'Authorization': f'Bearer {settings.REMNAWAVE_BEARER_TOKEN}',
                'Content-Type': 'application/json',
            },
            timeout=10,
        )

        if not rmn_resp.ok:
            return HttpResponseRedirect(
                f'{app_url}/cabinet/login?error=not_found&telegram={telegram_username or telegram_id}'
            )

        data = rmn_resp.json()
        user = data.get('response', data)
        short_uuid = user.get('shortUuid')

        return HttpResponseRedirect(
            f'{app_url}/cabinet/login?auth=telegram&shortUuid={short_uuid}'
        )

    except jwt.exceptions.PyJWTError as e:
        return HttpResponseRedirect(f'{app_url}/cabinet/login?error=telegram_jwt&detail={str(e)[:50]}')
    except Exception:
        return HttpResponseRedirect(f'{app_url}/cabinet/login?error=server')
