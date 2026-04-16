---
title: Promo Code System
type: concept
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [concept, promo]
---

# Promo Code System

Система промокодов с тремя типами: скидка, бонусные дни, подарок.

## Типы промокодов

### percent (скидка)
- `value` = процент скидки
- Применяется к итоговой цене (после реферальной скидки)
- `final = price - (price × value / 100)`

### days (бонусные дни)
- `value` = количество дней
- Добавляются после оплаты через `remnawave.extend_subscription()`
- Цена не меняется

### gift (подарок)
- `value` = количество дней
- Бесплатная активация через ActivateGiftView
- Не требует оплаты
- `payment_method = 'gift_promo'`

## Валидация

Проверки (в порядке выполнения):
1. Код существует (case-insensitive lookup)
2. `is_active = True`
3. `valid_until` не истёк или NULL
4. `times_used < max_uses`
5. Per-user limit не превышен
6. Если указан `plan` — должен совпадать
7. Если указаны `allowed_periods` — период должен быть в списке

## Winback Промокоды

Автоматическая генерация через `notify_expired_with_promo()`:

```
Триггер: подписка истекла 1 день назад (days_left == -1)

Антиспам:
  - Нет BACK-* промокодов для этого пользователя
  - description != 'winback_user_{id}'

Генерация:
  - code: 'BACK' + 5 random chars
  - promo_type: 'percent'
  - value: 10
  - max_uses: 1
  - per_user_limit: 1

Отправка через Telegram
```

## API Endpoints

| Endpoint | Auth | Описание |
|----------|------|----------|
| POST `/validate-promo/` | JWT | Проверка кода + расчёт скидки |
| POST `/activate-gift/` | JWT | Активация gift-промокода |
| GET `/promo/info/` | No | Инфо для лендинга (без auth) |

## Audit Trail

`PromoCodeUsage` фиксирует каждое применение:
- Кто, какой промокод, к какой подписке
- `bonus_days` (для days type)
- `discount_amount` (для percent type)

## См. также

- [[PromoCode Model]] — структура модели
- [[Subscription Lifecycle]] — интеграция в flow покупки
- [[Telegram Bot Integration]] — winback уведомления
