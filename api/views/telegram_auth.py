import requests
import jwt
from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
import json

TELEGRAM_JWKS_URL = 'https://oauth.telegram.org/.well-known/jwks.json'

# Cache for JWKS client
_jwks_client = None


def get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(TELEGRAM_JWKS_URL)
    return _jwks_client


def telegram_login(request):
    """Redirect-based flow: redirect to Telegram OAuth."""
    from urllib.parse import urlencode
    params = urlencode({
        'client_id': settings.TELEGRAM_BOT_ID,
        'redirect_uri': f'{settings.APP_URL}/api/auth/telegram/callback/',
        'response_type': 'code',
        'scope': 'openid profile',
    })
    return HttpResponseRedirect(f'https://oauth.telegram.org/auth?{params}')


@csrf_exempt
def telegram_callback(request):
    """Handle both:
    - POST with id_token (from JS SDK popup)
    - GET with code (from redirect flow)
    """
    app_url = settings.APP_URL

    # === POST: JS SDK sends id_token directly ===
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            id_token = body.get('id_token')
            if not id_token:
                return JsonResponse({'error': 'No id_token'}, status=400)

            user_data = verify_telegram_id_token(id_token)
            short_uuid = lookup_remnawave_user(user_data['telegram_id'])

            if short_uuid:
                return JsonResponse({'shortUuid': short_uuid})
            else:
                return JsonResponse({'error': 'not_found', 'telegram_id': user_data['telegram_id']}, status=404)

        except jwt.exceptions.PyJWTError as e:
            return JsonResponse({'error': 'jwt_invalid', 'detail': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': 'server', 'detail': str(e)}, status=500)

    # === GET: Redirect flow with authorization code ===
    code = request.GET.get('code')
    if not code:
        return HttpResponseRedirect(f'{app_url}/cabinet/login?error=no_telegram_code')

    try:
        # Exchange code for tokens
        import base64
        credentials = base64.b64encode(
            f'{settings.TELEGRAM_BOT_ID}:{settings.TELEGRAM_BOT_SECRET}'.encode()
        ).decode()

        token_resp = requests.post('https://oauth.telegram.org/token', data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': f'{app_url}/api/auth/telegram/callback/',
            'client_id': settings.TELEGRAM_BOT_ID,
        }, headers={
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }, timeout=10)

        if not token_resp.ok:
            return HttpResponseRedirect(f'{app_url}/cabinet/login?error=telegram_token')

        tokens = token_resp.json()
        id_token = tokens.get('id_token')

        if not id_token:
            return HttpResponseRedirect(f'{app_url}/cabinet/login?error=telegram_no_token')

        user_data = verify_telegram_id_token(id_token)
        short_uuid = lookup_remnawave_user(user_data['telegram_id'])

        if short_uuid:
            return HttpResponseRedirect(
                f'{app_url}/cabinet/login?auth=telegram&shortUuid={short_uuid}'
            )
        else:
            return HttpResponseRedirect(
                f'{app_url}/cabinet/login?error=not_found&telegram={user_data.get("username", user_data["telegram_id"])}'
            )

    except Exception:
        return HttpResponseRedirect(f'{app_url}/cabinet/login?error=server')


def verify_telegram_id_token(id_token):
    """Verify Telegram JWT id_token and extract user data."""
    client = get_jwks_client()
    signing_key = client.get_signing_key_from_jwt(id_token)

    decoded = jwt.decode(
        id_token,
        signing_key.key,
        algorithms=['RS256'],
        audience=str(settings.TELEGRAM_BOT_ID),
        issuer='https://oauth.telegram.org',
    )

    return {
        'telegram_id': decoded.get('id') or decoded.get('sub'),
        'name': decoded.get('name', ''),
        'username': decoded.get('preferred_username', ''),
        'picture': decoded.get('picture', ''),
    }


def lookup_remnawave_user(telegram_id):
    """Find user in Remnawave by Telegram ID, return shortUuid or None."""
    try:
        resp = requests.get(
            f'{settings.REMNAWAVE_API_URL}/users/by-telegram-id/{telegram_id}',
            headers={
                'Authorization': f'Bearer {settings.REMNAWAVE_BEARER_TOKEN}',
                'Content-Type': 'application/json',
            },
            timeout=10,
        )
        if resp.ok:
            data = resp.json()
            user = data.get('response', data)
            return user.get('shortUuid')
    except Exception:
        pass
    return None
