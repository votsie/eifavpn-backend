from django.urls import path, re_path
from .views.proxy import proxy_view
from .views.google_auth import google_login, google_callback
from .views.telegram_auth import telegram_auth

urlpatterns = [
    path('auth/google/', google_login, name='google_login'),
    path('auth/google/callback/', google_callback, name='google_callback'),
    path('auth/telegram/', telegram_auth, name='telegram_auth'),
    re_path(r'^proxy/(?P<path>.*)$', proxy_view, name='proxy'),
]
