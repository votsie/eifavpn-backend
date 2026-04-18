import logging

from .base import *

DEBUG = False

# Sentry — only if DSN is configured. Keeps dev/CI clean.
_sentry_dsn = os.environ.get('SENTRY_DSN', '').strip()
if _sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk.init(
        dsn=_sentry_dsn,
        integrations=[
            DjangoIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        environment=os.environ.get('SENTRY_ENVIRONMENT', 'prod'),
        traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.05')),
        send_default_pii=False,
    )

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'eifavpn.ru,www.eifavpn.ru').split(',')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'eifavpn_prod'),
        'USER': os.environ.get('DB_USER', 'eifavpn_prod'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

CORS_ALLOWED_ORIGINS = [
    'https://eifavpn.ru',
    'https://www.eifavpn.ru',
]

CSRF_TRUSTED_ORIGINS = [
    'https://eifavpn.ru',
    'https://www.eifavpn.ru',
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
