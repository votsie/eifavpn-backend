---
title: API Endpoints Reference
type: domain
domain: api
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [domain, api, endpoints]
---

# API Endpoints Reference

Полный список всех API-эндпоинтов проекта.

## URL-маршрутизация (eifavpn/urls.py)

```python
path('admin/',            admin.site.urls)
path('api/auth/',         include('accounts.urls'))
path('api/referral/',     include('accounts.referral_urls'))
path('api/subscriptions/', include('subscriptions.urls'))
path('api/',              include('api.urls'))
```

---

## Auth Endpoints — `/api/auth/`

Источник: [[Accounts App]]

| Method | Endpoint | Auth | View | Назначение |
|--------|----------|------|------|-----------|
| POST | `send-code/` | No | SendCodeView | Отправить 6-значный код на email |
| POST | `verify-code/` | No | VerifyCodeView | Верифицировать код + регистрация/вход |
| POST | `register/` | No | RegisterView | Legacy регистрация (email + password) |
| POST | `login/` | No | LoginView | Вход по email + password |
| POST | `refresh/` | No | TokenRefreshView | Обновить JWT access token |
| GET | `me/` | JWT | MeView | Получить профиль пользователя |
| PATCH | `me/` | JWT | MeView | Обновить first_name, avatar_url |
| POST | `logout/` | JWT | LogoutView | Blacklist refresh token |
| POST | `change-password/` | JWT | ChangePasswordView | Сменить пароль |
| POST | `delete-account/` | JWT | DeleteAccountView | Удалить аккаунт |
| POST | `telegram-webapp/` | No | TelegramWebAppAuthView | Вход через Telegram Mini App |
| POST | `link-email/` | JWT | LinkEmailView | Привязать email (отправить код) |
| POST | `link-email/verify/` | JWT | LinkEmailVerifyView | Подтвердить привязку email |
| POST | `link-telegram/` | JWT | LinkTelegramView | Привязать Telegram |
| GET | `link-google/` | JWT | link_google_redirect | Redirect на Google OAuth |

## Referral Endpoints — `/api/referral/`

| Method | Endpoint | Auth | View | Назначение |
|--------|----------|------|------|-----------|
| GET | `my/` | JWT | ReferralMyView | Код, ссылка, статистика рефералов |
| GET | `list/` | JWT | ReferralListView | Список приглашённых (masked email) |
| POST | `prepare-share/` | JWT | PrepareShareView | Telegram inline share message |

## OAuth Endpoints — `/api/`

Источник: [[API App]]

| Method | Endpoint | Auth | View | Назначение |
|--------|----------|------|------|-----------|
| GET | `auth/google/` | No | google_login | Redirect на Google OAuth |
| GET | `auth/google/callback/` | No | google_callback | Callback Google OAuth |
| GET | `auth/telegram/` | No | telegram_login | Redirect на Telegram OAuth |
| GET/POST | `auth/telegram/callback/` | No | telegram_callback | Callback Telegram OAuth |

## Proxy Endpoint — `/api/proxy/`

| Method | Endpoint | Auth | Назначение |
|--------|----------|------|-----------|
| ANY | `proxy/<path>` | Conditional | Проксирование к [[Remnawave]] API |

**Public**: `/system/stats`
**Authenticated**: `/users/`, `/hwid-user-devices/`, `/nodes`, `/hosts`, `/internal-squads`

## Subscription Endpoints — `/api/subscriptions/`

Источник: [[Subscriptions App]]

| Method | Endpoint | Auth | View | Назначение |
|--------|----------|------|------|-----------|
| GET | `plans/` | No | PlansView | Список тарифов с ценами |
| POST | `purchase/` | JWT | PurchaseView | Покупка подписки |
| GET | `my/` | JWT | MySubscriptionView | Текущая подписка + Remnawave данные |
| POST | `trial/` | JWT | TrialActivateView | Активация 3-дневного триала |
| POST | `trial-upgrade/` | JWT | TrialUpgradeView | 7 дней Pro за 1₽ |
| POST | `validate-promo/` | JWT | ValidatePromoView | Валидация промокода |
| POST | `activate-gift/` | JWT | ActivateGiftView | Активация подарочного промокода |
| GET | `promo/info/` | No | PromoInfoView | Инфо промокода для лендинга |
| GET | `rates/` | No | ExchangeRatesView | Курсы криптовалют |
| GET | `devices/` | JWT | UserDevicesView | Устройства пользователя |
| DELETE | `devices/` | JWT | UserDevicesView | Удалить устройство |

## Webhook Endpoints — `/api/subscriptions/`

| Method | Endpoint | Auth | Назначение |
|--------|----------|------|-----------|
| POST | `webhook/stars/` | CSRF exempt | [[Telegram Stars]] webhook |
| POST | `webhook/crypto/` | HMAC-SHA256 | [[CryptoPay]] webhook |
| POST | `webhook/wata/` | CSRF exempt | [[Wata H2H]] webhook |

## См. также

- [[Authentication Flows]] — детали потоков аутентификации
- [[Subscription Lifecycle]] — жизненный цикл подписки
- [[Proxy System]] — логика проксирования
