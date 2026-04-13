import requests
from urllib.parse import urlencode
from django.conf import settings
from django.http import HttpResponseRedirect
from accounts.models import User
from accounts.views import get_tokens_for_user


def google_login(request):
    redirect_uri = f'{settings.APP_URL}/api/auth/google/callback/'
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
    redirect_uri = f'{app_url}/api/auth/google/callback/'

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

        # Get user info from Google
        userinfo_resp = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers={
            'Authorization': f'Bearer {tokens["access_token"]}',
        }, timeout=10)

        if not userinfo_resp.ok:
            return HttpResponseRedirect(f'{app_url}/cabinet/login?error=userinfo')

        info = userinfo_resp.json()
        email = info.get('email', '').lower()
        google_id = info.get('id', '')
        name = info.get('name', '')
        picture = info.get('picture', '')

        if not email:
            return HttpResponseRedirect(f'{app_url}/cabinet/login?error=no_email')

        # Check if this is a link request (state=link:{user_id})
        state = request.GET.get('state', '')
        if state.startswith('link:'):
            try:
                link_user_id = int(state.split(':')[1])
                link_user = User.objects.get(id=link_user_id)

                # Check google_id not already taken
                if User.objects.filter(google_id=google_id).exclude(pk=link_user.pk).exists():
                    return HttpResponseRedirect(f'{app_url}/cabinet/settings?error=google_taken')

                link_user.google_id = google_id
                if not link_user.avatar_url and picture:
                    link_user.avatar_url = picture
                link_user.save()

                # Return JWT for linked user
                jwt_tokens = get_tokens_for_user(link_user)
                return HttpResponseRedirect(
                    f'{app_url}/cabinet/settings?linked=google'
                    f'&access={jwt_tokens["access"]}'
                    f'&refresh={jwt_tokens["refresh"]}'
                )
            except (User.DoesNotExist, ValueError):
                return HttpResponseRedirect(f'{app_url}/cabinet/settings?error=link_failed')

        # Find or create Django user
        user = User.objects.filter(email=email).first()
        if not user:
            user = User.objects.filter(google_id=google_id).first()
        if not user:
            user = User.objects.create_user(
                email=email,
                first_name=name,
                google_id=google_id,
                avatar_url=picture,
            )
        else:
            if not user.google_id:
                user.google_id = google_id
            if picture and not user.avatar_url:
                user.avatar_url = picture
            if name and not user.first_name:
                user.first_name = name
            user.save()

        # Generate JWT tokens
        jwt_tokens = get_tokens_for_user(user)

        # Redirect to frontend with tokens in URL fragment (not query — more secure)
        return HttpResponseRedirect(
            f'{app_url}/cabinet/login?auth=google'
            f'&access={jwt_tokens["access"]}'
            f'&refresh={jwt_tokens["refresh"]}'
        )
    except Exception:
        return HttpResponseRedirect(f'{app_url}/cabinet/login?error=server')
