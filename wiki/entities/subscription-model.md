---
title: Subscription Model
type: entity
app: accounts
file: accounts/models.py
status: stable
created: 2026-04-16
updated: 2026-04-17
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
| payment_method | CharField(32) | `stars` / `crypto` / `wata` / `trial` / `gift_promo` / `downgrade` (legacy) / `renewal_<method>` (временный prefix) |
| payment_id | CharField(255) | ID транзакции в платёжной системе |
| status | CharField(20) | `pending` / `paid` / `cancelled` / `expired` / `error` |
| created_at | DateTimeField | auto_now_add |
| expires_at | DateTimeField | Дата истечения |
| remnawave_uuid | UUIDField | UUID подписки в [[Remnawave]] |
| promo_code | FK(PromoCode) | Использованный промокод (nullable) |
| upgrade_from | FK(self, SET_NULL) | Ссылка на заменённую подписку при upgrade (см. [[Plan Upgrade]]) |

## Жизненный цикл статусов

```
pending ──webhook──→ paid ──expires_at<now──→ expired
   │                   │
   ├──error (Remnawave provisioning failed)
   │
   └──cancelled (user/admin cancel OR stale pending cleanup OR upgrade replaced old sub)
```

- **pending**: Платёж инициирован, ожидание webhook
- **paid**: Платёж подтверждён и Remnawave subscription создана/обновлена
- **error**: Платёж подтверждён, но Remnawave provisioning упал. Нужен retry или manual fix
- **cancelled**: Отменена пользователем ИЛИ заменена через upgrade (новая paid, старая cancelled)
- **expired**: Истёк срок (expires_at < now). Устанавливается cron-задачей (см. [[Auto-Renewal]])

## Idempotency (2026-04-17)

`process_payment_success(sub)` использует `select_for_update()` + проверку `status != 'paid'` — двойной webhook не создаёт дубли (важно для [[Telegram Stars]] которые ретраят при 5xx).

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
