from .base import *

DEBUG = True

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'dev.eifavpn.ru,localhost,127.0.0.1').split(',')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'eifavpn_dev'),
        'USER': os.environ.get('DB_USER', 'eifavpn_dev'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

CORS_ALLOW_ALL_ORIGINS = True
