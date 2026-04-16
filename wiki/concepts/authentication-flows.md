---
title: Authentication Flows
type: concept
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [concept, auth, oauth, jwt]
---

# Authentication Flows

EIFAVPN поддерживает 5 способов аутентификации. Все возвращают JWT пару (access + refresh).

## 1. Passwordless Email (основной)

```
Client                    Backend                    SMTP
  │                          │                         │
  │─POST /send-code/ {email}─▶                         │
  │                          │──Send 6-digit code──────▶│
  │◀─200 "Код отправлен"────│                         │
  │                          │                         │
  │─POST /verify-code/──────▶│                         │
  │  {email, code, name?,    │                         │
  │   referral_code?}        │                         │
  │                          │─Validate code (10min TTL)│
  │                          │─Create/find user         │
  │◀─200 {user, tokens}─────│                         │
```

**Rate limit**: 1 код/мин/email. Код одноразовый.
**Источник**: `accounts/views.py` — SendCodeView, VerifyCodeView

## 2. Email + Password (legacy)

```
POST /register/ {email, password, name?, referral_code?}
  → 201 {user, tokens}

POST /login/ {email, password}
  → 200 {user, tokens}
```

**Источник**: `accounts/views.py` — RegisterView, LoginView

## 3. Telegram Mini App (initData)

```
Telegram Mini App           Backend
  │                            │
  │─POST /telegram-webapp/─────▶
  │  {initData}                │
  │                            │─Parse & validate initData
  │                            │─Verify HMAC with BOT_TOKEN
  │                            │─Check lifetime ≤ 24h
  │                            │─Extract telegram_id
  │                            │─Find/create user (tg_{id}@eifavpn.ru)
  │◀─200 {user, tokens}───────│
```

**Library**: `init_data_py`. **Источник**: `accounts/views.py` — TelegramWebAppAuthView

## 4. Google OAuth 2.0

```
Client              Backend              Google
  │                    │                    │
  │─GET /auth/google/──▶                    │
  │◀─302 Redirect──────│──────────────────▶│
  │                    │                    │
  │◀───────────────────│◀─callback?code=...│
  │                    │                    │
  │                    │─Exchange code──────▶│
  │                    │◀─access_token──────│
  │                    │                    │
  │                    │─GET userinfo───────▶│
  │                    │◀─{email,name,pic}──│
  │                    │                    │
  │◀─302 /cabinet/login?auth=google&access=...&refresh=...
```

**Account linking**: `state=link:{user_id}` → обновление google_id
**Источник**: `api/views/google_auth.py`

## 5. Telegram OAuth 2.0

```
Client              Backend              Telegram OAuth
  │                    │                    │
  │─GET /auth/telegram/▶                    │
  │◀─302 Redirect──────│──────────────────▶│
  │                    │                    │
  │◀───────────────────│◀─callback?code=...│
  │                    │                    │
  │                    │─Exchange code──────▶│
  │                    │  (Basic Auth)       │
  │                    │◀─{id_token}────────│
  │                    │                    │
  │                    │─Verify RS256 JWT    │
  │                    │  via JWKS           │
  │◀─302 /cabinet/login?auth=telegram&access=...&refresh=...
```

**POST variant** (JS SDK): POST callback с `{id_token}` → JSON response
**Источник**: `api/views/telegram_auth.py`

## Account Linking

| Действие | Endpoint | Условия |
|---------|---------|---------|
| Link Email | POST `/link-email/` + `/link-email/verify/` | Только tg_* пользователи, не Google |
| Link Telegram | POST `/link-telegram/` | telegram_id не привязан |
| Link Google | GET `/link-google/` → OAuth flow | google_id не привязан |

## JWT Token Lifecycle

- **Access token**: 1 день
- **Refresh token**: 90 дней
- Rotation: новый refresh при каждом использовании
- Blacklist: старый refresh автоматически блэклистится

## См. также

- [[Accounts App]] — views
- [[API App]] — OAuth callbacks
- [[JWT Authentication]] — конфигурация токенов
