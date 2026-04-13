from django.urls import path
from django.conf import settings
from django.http import HttpResponseRedirect
from urllib.parse import urlencode
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.authentication import JWTAuthentication
from .views import (
    RegisterView, LoginView, MeView, LogoutView,
    ChangePasswordView, DeleteAccountView,
    SendCodeView, VerifyCodeView,
    TelegramWebAppAuthView,
    LinkEmailView, LinkEmailVerifyView, LinkTelegramView,
)
from .models import User


def link_google_redirect(request):
    """Redirect to Google OAuth with link state."""
    redirect_uri = f'{settings.APP_URL}/api/auth/google/callback/'
    # Get user from JWT
    try:
        auth = JWTAuthentication()
        result = auth.authenticate(request)
        user = result[0] if result else None
    except Exception:
        user = None

    if not user:
        return HttpResponseRedirect(f'{settings.APP_URL}/cabinet/login?error=auth_required')

    if user.google_id:
        return HttpResponseRedirect(f'{settings.APP_URL}/cabinet/settings?error=google_already_linked')

    params = urlencode({
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'email profile',
        'access_type': 'offline',
        'prompt': 'select_account',
        'state': f'link:{user.id}',
    })
    return HttpResponseRedirect(f'https://accounts.google.com/o/oauth2/auth?{params}')


urlpatterns = [
    path('send-code/', SendCodeView.as_view(), name='send_code'),
    path('verify-code/', VerifyCodeView.as_view(), name='verify_code'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', MeView.as_view(), name='me'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete_account'),
    path('telegram-webapp/', TelegramWebAppAuthView.as_view(), name='telegram_webapp'),
    path('link-email/', LinkEmailView.as_view(), name='link_email'),
    path('link-email/verify/', LinkEmailVerifyView.as_view(), name='link_email_verify'),
    path('link-telegram/', LinkTelegramView.as_view(), name='link_telegram'),
    path('link-google/', link_google_redirect, name='link_google'),
]
