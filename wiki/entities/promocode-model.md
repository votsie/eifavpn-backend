---
title: PromoCode Model
type: entity
app: accounts
file: accounts/models.py
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [entity, model, promo]
---

# PromoCode Model

Промокоды для скидок, бонусных дней и подарков.

## Поля (из анализа views)

| Поле | Тип | Описание |
|------|-----|----------|
| code | CharField | Уникальный код (case-insensitive) |
| promo_type | CharField | `percent` / `days` / `gift` |
| value | IntegerField | % скидки или кол-во дней |
| plan | CharField/None | Ограничение на тариф |
| allowed_periods | List/None | Допустимые периоды [1,3,6] |
| max_uses | IntegerField | Глобальный лимит использований |
| times_used | IntegerField | Текущее кол-во использований |
| per_user_limit | IntegerField | Лимит на пользователя |
| description | CharField | Метаданные (напр. `winback_user_123`) |
| is_active | BooleanField | Активен ли код |
| valid_until | DateTimeField | Срок действия (nullable) |
| created_by | FK(User) | Создатель (nullable) |

## Типы промокодов

### percent
Процентная скидка на стоимость подписки.
```
final_price = base_price - (base_price * value / 100)
```

### days
Бонусные дни к подписке (добавляются после оплаты).
```
remnawave.extend_subscription(uuid, value_days)
```

### gift
Бесплатная активация без оплаты. Активируется через ActivateGiftView.
- Создаёт/продлевает подписку на `value` дней
- `payment_method = 'gift_promo'`

## Валидация

Проверки при использовании:
1. Код существует (case-insensitive)
2. `is_active = True`
3. `valid_until` не истёк (или NULL)
4. `times_used < max_uses`
5. Per-user лимит не превышен
6. План/период соответствуют ограничениям

## PromoCodeUsage

Аудит-лог использования:

| Поле | Тип | Описание |
|------|-----|----------|
| promo | FK(PromoCode) | Промокод |
| user | FK(User) | Пользователь |
| subscription | FK(Subscription) | Подписка (nullable) |
| bonus_days | IntegerField | Добавленные дни |
| discount_amount | DecimalField | Сумма скидки |
| created_at | DateTimeField | auto_now_add |

## Winback промокоды

Автоматически генерируются через `notify_expired_with_promo()`:
- Код: `BACK` + 5 случайных символов
- Тип: `percent`, value: 10
- max_uses: 1, per_user_limit: 1
- description: `winback_user_{user_id}`
- Отправляется через Telegram через 1 день после истечения подписки

## См. также

- [[Promo Code System]] — полная логика
- [[Subscriptions App]] — ValidatePromoView, ActivateGiftView
- [[Telegram Bot Integration]] — отправка winback
