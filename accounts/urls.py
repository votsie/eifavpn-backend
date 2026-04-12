from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, MeView, LogoutView,
    ChangePasswordView, DeleteAccountView,
    SendCodeView, VerifyCodeView,
)

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
]
