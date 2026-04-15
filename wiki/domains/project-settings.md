---
title: Project Settings
domain: infrastructure
updated: 2026-04-16
---

# Project Settings

Конфигурация Django проекта. Настройки разделены на base/dev/prod модули.

## Файлы настроек

| Файл | Назначение |
|------|-----------|
| `eifavpn/settings/base.py` | Общие настройки для всех окружений |
| `eifavpn/settings/dev.py` | Разработка: DEBUG=True, CORS_ALLOW_ALL |
| `eifavpn/settings/prod.py` | Продакшен: DEBUG=False, strict CORS |
| `eifavpn/settings/__init__.py` | Пустой (выбор через DJANGO_SETTINGS_MODULE) |

## Installed Apps

**Django core:** admin, auth, contenttypes, sessions, messages, staticfiles
**Third-party:** rest_framework, rest_framework_simplejwt, rest_framework_simplejwt.token_blacklist, corsheaders
**Project:** accounts, subscriptions, api

## Middleware (порядок выполнения)

1. SecurityMiddleware — заголовки безопасности
2. CorsMiddleware — CORS (должен быть вторым)
3. SessionMiddleware
4. CommonMiddleware
5. CsrfViewMiddleware
6. AuthenticationMiddleware
7. MessageMiddleware
8. XFrameOptionsMiddleware

## [[JWT Authentication]]

```
ACCESS_TOKEN_LIFETIME = 1 день
REFRESH_TOKEN_LIFETIME = 90 дней
ROTATE_REFRESH_TOKENS = True
BLACKLIST_AFTER_ROTATION = True
AUTH_HEADER_TYPES = ('Bearer',)
```

## База данных

PostgreSQL через psycopg2-binary. Разные БД для dev/prod:

| Env | DB Name | DB User |
|-----|---------|---------|
| Dev | eifavpn_dev | eifavpn_dev |
| Prod | eifavpn_prod | eifavpn_prod |

## CORS

- **Dev**: `CORS_ALLOW_ALL_ORIGINS = True`
- **Prod**: Whitelist `eifavpn.ru`, `www.eifavpn.ru` + matching CSRF_TRUSTED_ORIGINS

## Email (SMTP)

Backend: `django.core.mail.backends.smtp.EmailBackend`
TLS по умолчанию, порт 587. Отправитель: `noreply@eifavpn.ru`

## Локализация

- `LANGUAGE_CODE = 'ru-ru'`
- `TIME_ZONE = 'UTC'` (все timestamps в UTC)
- `USE_TZ = True`

## Переменные окружения

### Критичные
- `SECRET_KEY`, `DB_PASSWORD`, `DJANGO_SETTINGS_MODULE`

### Внешние сервисы
- `REMNAWAVE_API_URL`, `REMNAWAVE_BEARER_TOKEN`, `REMNAWAVE_DEFAULT_SQUAD`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_ID`, `TELEGRAM_BOT_SECRET`
- `CRYPTOPAY_TOKEN`, `WATA_TOKEN`
- `APP_URL` (фронтенд URL, default: `http://localhost:5173`)

### Email
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`

## См. также

- [[CI CD Pipeline]] — деплой конфигурация
- [[API Endpoints Reference]] — маршрутизация
