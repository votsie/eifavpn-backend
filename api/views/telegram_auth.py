import json
import jwt as pyjwt
import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from accounts.models import User
from accounts.views import get_tokens_for_user

TELEGRAM_JWKS_URL = 'https://oauth.telegram.org/.well-known/jwks.json'

_jwks_client = None


def get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = pyjwt.PyJWKClient(TELEGRAM_JWKS_URL)
    return _jwks_client


def telegram_login(request):
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
    app_url = settings.APP_URL

    # POST: JS SDK sends id_token
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            id_token = body.get('id_token')
            if not id_token:
                return JsonResponse({'error': 'No id_token'}, status=400)

            tg_data = verify_telegram_token(id_token)
            user = find_or_create_user(tg_data)
            tokens = get_tokens_for_user(user)

            return JsonResponse({
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                },
                'tokens': tokens,
            })
        except pyjwt.exceptions.PyJWTError as e:
            return JsonResponse({'error': 'jwt_invalid', 'detail': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': 'server', 'detail': str(e)}, status=500)

    # GET: Redirect flow with code
    code = request.GET.get('code')
    if not code:
        return HttpResponseRedirect(f'{app_url}/cabinet/login?error=no_telegram_code')

    try:
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

        id_token = token_resp.json().get('id_token')
        if not id_token:
            return HttpResponseRedirect(f'{app_url}/cabinet/login?error=telegram_no_token')

        tg_data = verify_telegram_token(id_token)
        user = find_or_create_user(tg_data)
        tokens = get_tokens_for_user(user)

        return HttpResponseRedirect(
            f'{app_url}/cabinet/login?auth=telegram'
            f'&access={tokens["access"]}'
            f'&refresh={tokens["refresh"]}'
        )
    except Exception:
        return HttpResponseRedirect(f'{app_url}/cabinet/login?error=server')


def verify_telegram_token(id_token):
    client = get_jwks_client()
    signing_key = client.get_signing_key_from_jwt(id_token)
    decoded = pyjwt.decode(
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


def find_or_create_user(tg_data):
    telegram_id = int(tg_data['telegram_id'])

    user = User.objects.filter(telegram_id=telegram_id).first()
    if user:
        return user

    # Create new user (no email from Telegram — use placeholder)
    email = f'tg_{telegram_id}@eifavpn.ru'
    user = User.objects.create_user(
        email=email,
        first_name=tg_data.get('name', ''),
        telegram_id=telegram_id,
        avatar_url=tg_data.get('picture', ''),
    )
    return user
