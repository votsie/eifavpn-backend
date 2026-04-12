from django.urls import path, re_path
from .views.proxy import proxy_view
from .views.google_auth import google_login, google_callback
from .views.telegram_auth import telegram_login, telegram_callback

urlpatterns = [
    path('auth/google/', google_login, name='google_login'),
    path('auth/google/callback/', google_callback, name='google_callback'),
    path('auth/telegram/', telegram_login, name='telegram_login'),
    path('auth/telegram/callback/', telegram_callback, name='telegram_callback'),
    re_path(r'^proxy/(?P<path>.*)$', proxy_view, name='proxy'),
]
