---
title: Accounts App
type: source
app: accounts
updated: 2026-04-16
---

# Accounts App

Django-приложение для управления пользователями, аутентификации и реферальной системы.

## Файлы

| Файл | Строк | Назначение |
|------|-------|-----------|
| `models.py` | ~150 | [[User Model]], [[Subscription Model]], [[Referral Model]], [[EmailVerification Model]] |
| `views.py` | ~500 | 13 API views: auth, profile, linking, referrals |
| `serializers.py` | ~100 | RegisterSerializer, LoginSerializer, UserSerializer, UpdateProfileSerializer |
| `urls.py` | ~20 | 15 auth-эндпоинтов |
| `referral_urls.py` | ~10 | 3 реферальных эндпоинта |
| `admin.py` | ~5 | Пустой |

## Модели

- **[[User Model]]** — Кастомная модель (extends AbstractUser), email как USERNAME_FIELD
- **[[Subscription Model]]** — Подписки пользователей (plan, period, status, payment)
- **[[Referral Model]]** — Связь referrer → referred + bonus tracking
- **[[EmailVerification Model]]** — 6-значные коды верификации (10 мин TTL)

## Сериализаторы

### RegisterSerializer
- Поля: `email`, `password` (min 6), `name`, `referral_code`
- Валидация: email уникальность (case-insensitive)
- Создание: User + referred_by FK если referral_code указан

### LoginSerializer
- Поля: `email`, `password`
- Без кастомной валидации

### UserSerializer (read-mostly)
- Все поля User + computed: `has_subscription`, `current_plan`
- `has_subscription()`: exists(status='paid', expires_at > now)
- `current_plan()`: dict {plan, expires_at, period} или None

### UpdateProfileSerializer
- Editable: `first_name`, `avatar_url`

## Views

### Публичные (AllowAny)

| View | Method | Endpoint | Описание |
|------|--------|----------|----------|
| SendCodeView | POST | `/send-code/` | Отправка 6-значного кода на email. Rate limit: 1/мин/email |
| VerifyCodeView | POST | `/verify-code/` | Верификация кода + auto-register/login |
| RegisterView | POST | `/register/` | Legacy регистрация с паролем |
| LoginView | POST | `/login/` | Email + password вход |
| TelegramWebAppAuthView | POST | `/telegram-webapp/` | Вход через Telegram Mini App initData |

### Защищённые (IsAuthenticated)

| View | Method | Endpoint | Описание |
|------|--------|----------|----------|
| MeView | GET/PATCH | `/me/` | Профиль / обновление |
| LogoutView | POST | `/logout/` | Blacklist refresh token |
| ChangePasswordView | POST | `/change-password/` | Смена пароля (OAuth users: без старого) |
| DeleteAccountView | POST | `/delete-account/` | Удаление + disable в [[Remnawave]] |
| LinkEmailView | POST | `/link-email/` | Привязка email (для TG-пользователей) |
| LinkEmailVerifyView | POST | `/link-email/verify/` | Подтверждение привязки email |
| LinkTelegramView | POST | `/link-telegram/` | Привязка Telegram к существующему аккаунту |
| PrepareShareView | POST | `/prepare-share/` | Telegram inline sharing рефералки |

### Реферальные Views

| View | Method | Endpoint | Описание |
|------|--------|----------|----------|
| ReferralMyView | GET | `/referral/my/` | Код, ссылка, total_referrals, bonus_days |
| ReferralListView | GET | `/referral/list/` | Список рефералов (masked emails) |

## Ключевая логика

### Email-маскирование
`_mask_email("user@example.com")` → `"us***@example.com"`
Используется в ReferralListView для приватности.

### Passwordless Auth Flow
SendCodeView → VerifyCodeView — основной flow аутентификации.
Коды одноразовые, 10 мин TTL, rate limit 1/мин/email.

### Account Linking
- Telegram users (tg_*@eifavpn.ru) могут привязать real email
- Google users НЕ могут менять email
- Любой user может привязать Telegram (если не привязан)

## Миграции

| # | Дата | Изменения |
|---|------|----------|
| 0001 | 2026-04-12 09:55 | User, Subscription, Referral |
| 0002 | 2026-04-12 10:55 | +used_trial, +used_trial_upgrade |
| 0003 | 2026-04-12 16:37 | +EmailVerification, +email_verified |

## См. также

- [[Authentication Flows]] — полные flow диаграммы
- [[Referral System]] — детали реферальной системы
- [[API Endpoints Reference]] — все эндпоинты
