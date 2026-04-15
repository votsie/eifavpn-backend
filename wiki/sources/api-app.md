---
title: API App
type: source
app: api
updated: 2026-04-16
---

# API App

Django-приложение для OAuth-аутентификации и проксирования к [[Remnawave]].

## Файлы

| Файл | Назначение |
|------|-----------|
| `urls.py` | Маршрутизация: OAuth + proxy |
| `views/google_auth.py` | Google OAuth 2.0 login/callback |
| `views/telegram_auth.py` | Telegram OAuth 2.0 login/callback |
| `views/proxy.py` | Secure proxy к [[Remnawave]] API |
| `views.py` | Пустой |
| `models.py` | Пустой (модели в accounts) |

## Google OAuth 2.0

### `google_login(request)` — GET `/api/auth/google/`
Redirect на Google OAuth consent screen:
- scope: `email profile`
- access_type: `offline`
- prompt: `select_account`

### `google_callback(request)` — GET `/api/auth/google/callback/`
Обработка callback:

1. **Token exchange**: POST `https://oauth2.googleapis.com/token` (10s timeout)
2. **User info**: GET `https://www.googleapis.com/oauth2/v2/userinfo`
3. **Account linking** (если `state=link:{user_id}`):
   - Проверка google_id не занят
   - Обновление user.google_id, avatar_url
   - Redirect: `/cabinet/settings?linked=google&access=...&refresh=...`
4. **Login/Register** (без state):
   - Поиск по email → google_id
   - Создание user если не найден
   - Redirect: `/cabinet/login?auth=google&access=...&refresh=...`

> [!gap] Security Note
> JWT токены передаются в query string URL. Рекомендуется использовать URL fragments или HttpOnly cookies.

## Telegram OAuth 2.0

### `telegram_login(request)` — GET `/api/auth/telegram/`
Redirect на Telegram OAuth:
- scope: `openid profile`
- Redirect URI: `{APP_URL}/api/auth/telegram/callback/`

### `telegram_callback(request)` — GET/POST `/api/auth/telegram/callback/`

**POST flow** (Telegram JS SDK):
- Body: `{"id_token": "<JWT>"}`
- Верификация JWT через JWKS (`RS256`)
- Возврат JSON: `{user, tokens}`

**GET flow** (OAuth redirect):
- Token exchange с Basic Auth: `base64(BOT_ID:BOT_SECRET)`
- POST `https://oauth.telegram.org/token`
- Верификация id_token через JWKS
- Redirect: `/cabinet/login?auth=telegram&access=...&refresh=...`

### `verify_telegram_token(id_token)`
- JWKS URL: `https://oauth.telegram.org/.well-known/jwks.json`
- Algorithm: RS256
- Audience: TELEGRAM_BOT_ID
- Issuer: `https://oauth.telegram.org`

### `find_or_create_user(tg_data)`
- Lookup по telegram_id
- Создание с email `tg_{telegram_id}@eifavpn.ru`
- Password unusable

## [[Proxy System]]

### `proxy_view(request, path='')` — ANY `/api/proxy/<path>`

Secure gateway к [[Remnawave]] API с:

**Whitelist эндпоинтов:**
- Public: `/system/stats`
- Auth required: `/users/`, `/hwid-user-devices/`, `/nodes`, `/hosts`, `/internal-squads`

**Security layers:**
1. Endpoint whitelist (403 если не в списке)
2. JWT auth для не-public эндпоинтов
3. Ownership validation для `/users/` (только свой UUID)
4. Body filtering для PATCH: только `{uuid, email, telegramId, description}`

**Upstream:**
```
URL: {REMNAWAVE_API_URL}{endpoint}
Headers: Bearer {REMNAWAVE_BEARER_TOKEN}
Timeout: 15s
```

## Ошибки

| Код | Ситуация |
|-----|---------|
| 302→error=no_code | Нет authorization code |
| 302→error=token_exchange | Ошибка обмена кода на токен |
| 302→error=google_taken | Google ID уже привязан к другому аккаунту |
| 401 | JWT не валиден (proxy) |
| 403 | Endpoint не в whitelist / access denied |
| 502 | Upstream timeout/error |

## См. также

- [[Authentication Flows]] — полные flow диаграммы
- [[Proxy System]] — детали проксирования
- [[Remnawave]] — внешний сервис
