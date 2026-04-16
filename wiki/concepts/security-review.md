---
title: Security Review
type: concept
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [security, review, hardening]
---

# Security Review

Результаты аудита безопасности бэкенда, проведённого 2026-04-16. Все P0 и P1 проблемы исправлены.

## P0 — Критичные (исправлено)

### JWT токены в URL query параметрах
- **Было**: OAuth callbacks (`google_callback`, `telegram_callback`) передавали access/refresh токены в `?access=...&refresh=...`
- **Риск**: Токены попадают в server access logs, browser history, Referer headers
- **Исправлено**: Перенесено в URL fragment `#access=...&refresh=...` — фрагменты не отправляются на сервер
- **Файлы**: `api/views/google_auth.py`, `api/views/telegram_auth.py`
- **См.**: [[Authentication Flows]], [[JWT Authentication]]

### Wata webhook без верификации
- **Было**: Любой POST с `transactionStatus=Paid` принимался как успешная оплата
- **Риск**: Подделка платежей при известном subscription ID
- **Исправлено**: Добавлена server-to-server верификация через Wata API (`_verify_wata_payment`). Fail-closed: при недоступности API платёж отклоняется
- **Файл**: `subscriptions/views.py`
- **См.**: [[Wata H2H]], [[Payment Processing]]

### Глобальный socket.setdefaulttimeout
- **Было**: `socket.setdefaulttimeout(10)` в `SendCodeView` и `LinkEmailView` — влияет на ВСЕ сокеты процесса
- **Риск**: Непредсказуемые таймауты в Remnawave, Telegram API, CryptoPay вызовах в том же gunicorn worker
- **Исправлено**: Удалено, заменено на `EMAIL_TIMEOUT = 10` в settings (скопировано только на SMTP backend)
- **Файлы**: `accounts/views.py`, `eifavpn/settings/base.py`

## P1 — Важные (исправлено)

### Google OAuth state без подписи
- **Было**: `state=link:{user_id}` — предсказуемо при известном ID
- **Риск**: Hijack привязки Google аккаунта к чужому пользователю
- **Исправлено**: HMAC-SHA256 подпись state через `_sign_state()` / `verify_oauth_state()` с использованием `SECRET_KEY`
- **Файлы**: `accounts/urls.py`, `api/views/google_auth.py`
- **См.**: [[Authentication Flows]]

### Email verification code через random
- **Было**: `random.randint(0, 9)` — Mersenne Twister, предсказуем при наблюдении выходов
- **Исправлено**: `secrets.randbelow(10)` — криптографически безопасный PRNG
- **Файл**: `accounts/models.py`
- **См.**: [[EmailVerification Model]]

### Отсутствие SECURE_* headers в production
- **Было**: Только `SECURE_PROXY_SSL_HEADER`
- **Исправлено**: Добавлены `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS=31536000`, `SECURE_HSTS_PRELOAD`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`
- **Файл**: `eifavpn/settings/prod.py`
- **См.**: [[Project Settings]]

### expires_at рассчитывается при создании, не при оплате
- **Было**: `expires_at = now + period * 30` в `PurchaseView` (момент инициации покупки)
- **Риск**: Пользователь теряет дни, если оплата задерживается
- **Исправлено**: `process_payment_success` пересчитывает `expires_at` от момента оплаты
- **Файл**: `subscriptions/views.py`
- **См.**: [[Subscription Lifecycle]], [[Subscription Model]]

## P2 — Улучшения (исправлено)

### Stars webhook без secret token
- **Исправлено**: Проверка `X-Telegram-Bot-Api-Secret-Token` header (через `TELEGRAM_WEBHOOK_SECRET` в settings)
- **См.**: [[Telegram Stars]], [[Payment Processing]]

### Google Client ID в .env.example
- **Исправлено**: Заменён на placeholder
- **См.**: [[Project Settings]]

## Остаточные рекомендации

| Задача | Статус |
|--------|--------|
| Rate limiting на login/register | Не реализовано |
| Тесты для auth + payment flows | Не реализовано |
| PromoCode модель (dead code paths) | Не реализовано |
| SSH keys вместо passwords в CI/CD | Не реализовано |
| Health check endpoint (/healthz) | Не реализовано |

## См. также

- [[Authentication Flows]] — Потоки аутентификации
- [[Payment Processing]] — Платёжные шлюзы и webhooks
- [[Subscription Lifecycle]] — Жизненный цикл подписки
- [[Project Settings]] — Конфигурация Django
- [[Proxy System]] — Безопасный прокси к Remnawave
