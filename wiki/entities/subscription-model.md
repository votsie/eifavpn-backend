---
title: Subscription Model
type: entity
app: accounts
file: accounts/models.py
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [entity, model, subscription]
---

# Subscription Model

Запись о подписке пользователя на VPN-тариф.

## Поля

| Поле | Тип | Описание |
|------|-----|----------|
| user | FK(User, CASCADE) | Владелец (related_name='subscriptions') |
| plan | CharField(20) | `standard` / `pro` / `max` |
| period_months | IntegerField | 1, 3, 6, 12 (или 0 для trial-upgrade) |
| price_paid | DecimalField(10,2) | Оплаченная сумма в RUB |
| payment_method | CharField(32) | `stars` / `crypto` / `wata` / `trial` / `gift_promo` |
| payment_id | CharField(255) | ID транзакции в платёжной системе |
| status | CharField(20) | `pending` / `paid` / `cancelled` / `expired` |
| created_at | DateTimeField | auto_now_add |
| expires_at | DateTimeField | Дата истечения |
| remnawave_uuid | UUIDField | UUID подписки в [[Remnawave]] |
| promo_code | FK(PromoCode) | Использованный промокод (nullable) |

## Жизненный цикл статусов

```
pending → paid → expired
    ↓
 cancelled
```

- **pending**: Платёж инициирован, ожидание webhook
- **paid**: Платёж подтверждён, подписка активна
- **cancelled**: Отменена пользователем
- **expired**: Истёк срок (expires_at < now)

## Ordering

`-created_at` — newest first.

## Запросы

### Активная подписка
```python
Subscription.objects.filter(
    user=user, status='paid', expires_at__gt=now()
).order_by('-expires_at').first()
```

### Stale pending cleanup
При новой покупке все pending-подписки пользователя отменяются.

## Связи

- `user` → [[User Model]]
- `promo_code` → [[PromoCode Model]]
- ← [[Referral Model]] (subscription FK)

## См. также

- [[Subscription Lifecycle]] — полный flow
- [[Payment Processing]] — создание invoices и webhooks
- [[Subscriptions App]] — views
