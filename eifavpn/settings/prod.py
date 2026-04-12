from .base import *

DEBUG = False

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
