---
title: Subscription Lifecycle
type: concept
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [concept, subscription, payment, trial]
---

# Subscription Lifecycle

Полный жизненный цикл подписки от триала до winback.

## Основные сценарии

### 1. Trial Flow (бесплатный)

```
POST /trial/
  │
  ├─ Проверки: used_trial=False, нет подписок
  ├─ select_for_update() — защита от race condition
  ├─ remnawave.create_subscription(user, 'max', days=3)
  ├─ user.used_trial = True
  ├─ Subscription(plan='max', period=0, price=0, method='trial', status='paid')
  │
  └─ Response: {success, plan='max', days=3, subscription_url, expires_at}
```

### 2. Trial Upgrade (1₽ за 7 дней Pro)

```
POST /trial-upgrade/ {payment_method}
  │
  ├─ Проверки: used_trial=True, used_trial_upgrade=False
  ├─ Cancel stale pending subscriptions
  ├─ Subscription(plan='pro', period=0, price=1, status='pending')
  ├─ Create invoice (1₽)
  │
  └─ Webhook → process_payment_success()
       ├─ remnawave.update_subscription(uuid, 'pro', days=7)
       ├─ user.used_trial_upgrade = True
       └─ sub.status = 'paid'
```

### 3. Standard Purchase

```
POST /purchase/ {plan, period, payment_method, promo_code?}
  │
  ├─ Validate plan/period/method
  ├─ Calculate price (base - referral - promo discounts)
  ├─ Cancel stale pending subs
  ├─ Subscription(status='pending')
  ├─ Create invoice (Stars/Crypto/Wata)
  │
  └─ Webhook → process_payment_success()
       ├─ Create/update Remnawave subscription
       ├─ sub.status = 'paid'
       ├─ Apply promo bonuses
       ├─ Apply referral bonus (+7 days to referrer)
       └─ Send notifications
```

### 4. Gift Promo Activation

```
POST /activate-gift/ {code}
  │
  ├─ Validate promo (type='gift')
  ├─ If no remnawave_uuid: create_subscription()
  ├─ If remnawave_uuid: extend_subscription(days)
  ├─ Record PromoCodeUsage
  ├─ Subscription(method='gift_promo', status='paid')
  │
  └─ Response: {success, days_added, plan, expires_at}
```

## Ценообразование

```
base_price = PRICING[plan][period] × period

if user.referred_by:
    referral_discount = base_price × 10%
    price = base_price - referral_discount

if promo_code:
    if promo.type == 'percent':
        promo_discount = price × promo.value%
        price = price - promo_discount
    elif promo.type == 'days':
        bonus_days = promo.value  # added after payment

final_price = max(price, 1₽)
```

## process_payment_success(sub)

Центральный обработчик после подтверждения платежа:

```
1. Remnawave
   ├─ Если есть uuid → update_subscription(uuid, plan, period)
   └─ Если нет uuid → create_subscription(user, plan, period)
       └─ Сохранить uuid, shortUuid, subscriptionUrl

2. sub.status = 'paid'

3. Trial upgrade? → user.used_trial_upgrade = True

4. Promo code?
   ├─ days → extend_subscription(uuid, bonus_days)
   ├─ percent → record discount amount
   └─ PromoCodeUsage + increment times_used

5. Referral?
   ├─ Проверка: referred_by exists, bonus not applied
   ├─ extend_subscription(referrer.uuid, 7)
   ├─ referrer.referral_bonus_days += 7
   └─ Referral(bonus_applied=True)

6. Notifications
   ├─ User: notify_purchase_success()
   └─ Admin: notify_payment_success()
```

## Expiry & Winback

Ежедневный cron `run_subscription_notifications()`:

| days_left | Действие |
|-----------|---------|
| 3 | `notify_expiring(3)` — "Подписка заканчивается через 3 дня" |
| 1 | `notify_expiring(1)` — "Подписка заканчивается завтра!" |
| 0 | `notify_expired()` — "Подписка истекла" |
| -1 | `notify_expired_with_promo()` — Персональный промокод 10% |

## Статусы подписки

```
┌─────────┐    webhook    ┌──────┐    expires_at    ┌─────────┐
│ pending │───────────────▶│ paid │────────────────▶│ expired │
└─────────┘               └──────┘                  └─────────┘
     │                                                    
     ▼                                                    
┌───────────┐                                             
│ cancelled │  (stale cleanup)                            
└───────────┘                                             
```

## См. также

- [[Subscriptions App]] — views и webhooks
- [[Payment Processing]] — создание invoices
- [[Remnawave Integration]] — CRUD подписок
- [[Referral System]] — бонусы
- [[Promo Code System]] — промокоды
