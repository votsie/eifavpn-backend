import requests
from urllib.parse import urlencode
from django.conf import settings
from django.http import HttpResponseRedirect


def google_login(request):
    redirect_uri = f'{settings.APP_URL}/api/auth/google/callback'
    params = urlencode({
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'email profile',
        'access_type': 'offline',
        'prompt': 'select_account',
    })
    return HttpResponseRedirect(f'https://accounts.google.com/o/oauth2/auth?{params}')


def google_callback(request):
    code = request.GET.get('code')
    app_url = settings.APP_URL
    redirect_uri = f'{app_url}/api/auth/google/callback'

    if not code:
        return HttpResponseRedirect(f'{app_url}/cabinet/login?error=no_code')

    try:
        # Exchange code for tokens
        token_resp = requests.post('https://oauth2.googleapis.com/token', data={
            'code': code,
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }, timeout=10)

        if not token_resp.ok:
            return HttpResponseRedirect(f'{app_url}/cabinet/login?error=token_exchange')

        tokens = token_resp.json()

        # Get user info
        userinfo_resp = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers={
            'Authorization': f'Bearer {tokens["access_token"]}',
        }, timeout=10)

        if not userinfo_resp.ok:
            return HttpResponseRedirect(f'{app_url}/cabinet/login?error=userinfo')

        email = userinfo_resp.json().get('email')
        if not email:
            return HttpResponseRedirect(f'{app_url}/cabinet/login?error=no_email')

        # Look up in Remnawave
        rmn_resp = requests.get(
            f'{settings.REMNAWAVE_API_URL}/users/by-email/{email}',
            headers={
                'Authorization': f'Bearer {settings.REMNAWAVE_BEARER_TOKEN}',
                'Content-Type': 'application/json',
            },
            timeout=10,
        )

        if not rmn_resp.ok:
            return HttpResponseRedirect(
                f'{app_url}/cabinet/login?error=not_found&email={email}'
            )

        data = rmn_resp.json()
        user = data.get('response', data)
        short_uuid = user.get('shortUuid')

        return HttpResponseRedirect(
            f'{app_url}/cabinet/login?auth=google&shortUuid={short_uuid}'
        )
    except Exception as e:
        return HttpResponseRedirect(f'{app_url}/cabinet/login?error=server')
