---
title: Subscriptions App
type: source
app: subscriptions
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [source, subscriptions, payment]
---

# Subscriptions App

Основной бизнес-модуль: тарифы, покупки, платежи, webhooks, уведомления, промокоды.

## Файлы

| Файл | Строк | Назначение |
|------|-------|-----------|
| `views.py` | ~858 | Основная бизнес-логика: 8+ views, webhooks, payment helpers |
| `plans.py` | ~70 | Определения тарифов и цен |
| `remnawave.py` | ~123 | Клиент [[Remnawave]] API |
| `notifications.py` | ~268 | Telegram-уведомления |
| `urls.py` | ~15 | URL-маршрутизация |
| `models.py` | — | Пустой (модели в accounts) |

## Тарифы (plans.py)

### Планы

| Plan | Серверы | Устройства | Трафик | Adblock | P2P |
|------|---------|-----------|--------|---------|-----|
| Standard | 7 | 3 | 1 TB/мес | No | No |
| Pro | 10 | 4 | Unlimited | Yes | No |
| Max | 14 | 6 | Unlimited | Yes | Yes |

### Цены (RUB/мес)

| Plan | 1 мес | 3 мес | 6 мес | 12 мес |
|------|-------|-------|-------|--------|
| Standard | 69 | 59 | 55 | 45 |
| Pro | 99 | 89 | 79 | 65 |
| Max | 149 | 129 | 119 | 99 |

Total = per_month × period. Пример: Pro 6 мес = 89 × 6 = 534₽

### Константы
- `REFERRAL_DISCOUNT_PERCENT = 10`
- `REFERRAL_BONUS_DAYS = 7`
- `DEFAULT_SQUAD = '38d5757f-a45a-4144-b4b3-fd3f5facb5dd'`

## Views

### PlansView — GET `/plans/` (AllowAny)
Список тарифов с ценами. Public endpoint для лендинга.

### PurchaseView — POST `/purchase/` (JWT)
Инициация покупки. См. [[Payment Processing]].

**Body**: `{plan, period, payment_method, crypto_asset?, promo_code?}`

**Расчёт цены:**
```
base = PRICING[plan][period] × period
referral_discount = base × 10% (если referred_by)
promo_discount = (base - referral) × promo.value% (если percent)
bonus_days = promo.value (если days)
total = max(base - discounts, 1₽)
```

### MySubscriptionView — GET `/my/` (JWT)
Текущая подписка + real-time данные из [[Remnawave]]:
- Traffic usage, online status, device limit
- Backfill subscription_url если отсутствует

### TrialActivateView — POST `/trial/` (JWT)
3-дневный MAX триал. Одноразовый:
- `select_for_update()` для защиты от race conditions
- Проверка: used_trial=False, нет подписок
- Создание в [[Remnawave]] + local Subscription (price=0, method='trial')

### TrialUpgradeView — POST `/trial-upgrade/` (JWT)
7 дней Pro за 1₽. После триала:
- Проверка: used_trial=True, used_trial_upgrade=False
- Создание invoice за 1₽

### ValidatePromoView — POST `/validate-promo/` (JWT)
Валидация промокода перед покупкой. Возвращает тип, скидку, итоговую цену.

### ActivateGiftView — POST `/activate-gift/` (JWT)
Активация подарочного промокода (type='gift') без оплаты.

### ExchangeRatesView — GET `/rates/` (AllowAny)
Курсы криптовалют (USDT, TON, BTC) + конвертация.

### UserDevicesView — GET/DELETE `/devices/` (JWT)
Список и удаление устройств через [[Remnawave]].

## Webhooks

| Endpoint | Источник | Верификация |
|----------|---------|-------------|
| `webhook/stars/` | Telegram Bot API | CSRF exempt |
| `webhook/crypto/` | [[CryptoPay]] | HMAC-SHA256 |
| `webhook/wata/` | [[Wata H2H]] | CSRF exempt |

Все вызывают `process_payment_success(sub)`.

## process_payment_success(sub)

Центральная функция после подтверждения платежа:

1. Create/Update подписки в [[Remnawave]]
2. `sub.status = 'paid'`
3. Mark trial_upgrade если price=1₽
4. Apply promo bonus (days → extend, percent → record discount)
5. Apply referral bonus (+7 дней реферреру)
6. Send Telegram notification

## Уведомления (notifications.py)

| Функция | Триггер |
|---------|---------|
| `send_welcome()` | /start команда бота |
| `notify_purchase_success()` | После оплаты |
| `notify_expiring(days)` | 3 дня и 1 день до истечения |
| `notify_expired()` | В день истечения |
| `notify_expired_with_promo()` | +1 день после истечения (winback) |
| `run_subscription_notifications()` | Cron job (ежедневно) |

## См. также

- [[Subscription Lifecycle]] — полный flow
- [[Payment Processing]] — детали платежей
- [[Remnawave Integration]] — API клиент
- [[Promo Code System]] — промокоды
- [[Telegram Bot Integration]] — уведомления
