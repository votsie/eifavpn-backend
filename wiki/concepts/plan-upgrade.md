---
title: Plan Upgrade
type: concept
status: stable
created: 2026-04-17
updated: 2026-04-17
tags: [concept, subscription, payment]
---

# Plan Upgrade

Pro-rata смена тарифа вверх. **Понижение тарифа отключено** (2026-04-17) — пользователь на Max не видит опции "перейти на Standard/Pro".

## Алгоритм (subscriptions/plans.py)

`get_upgrade_price(current_sub, new_plan, new_period)` возвращает:

| Поле | Описание |
|------|----------|
| `is_upgrade` | True если `PLAN_TIERS[new] > PLAN_TIERS[current]` ИЛИ та же тир но больше период |
| `charge_amount` | Сумма к доплате (pro-rata): `new_total - current_credit` |
| `current_credit` | Остаток стоимости по текущему плану: `daily_rate × remaining_days` |
| `new_total` | Полная стоимость нового плана/периода |
| `remaining_days` | Дней до истечения текущей подписки |

Plan tiers: `{standard: 1, pro: 2, max: 3}`.

## Flow

1. **Фронт**: `Purchase.jsx` вызывает `GET /api/subscriptions/upgrade-preview/?plan=X&period=Y`
2. **Фильтр**: `setUpgradePreview(data?.is_upgrade ? data : null)` — downgrade скрыт в UI
3. **Upgrade**: пользователь нажимает "Перейти на X — 99₽" → `POST /api/subscriptions/upgrade/`
4. **Backend `UpgradeView`**:
   - `get_upgrade_price` → если `not is_upgrade` → 400 "Понижение тарифа недоступно"
   - Создаёт pending Subscription с `upgrade_from=active_sub`
   - Генерирует invoice через `create_*_invoice()` на сумму `charge_amount`
   - Возвращает `{type: 'upgrade', charge_amount, payment_url}`
5. **Webhook** → `process_payment_success`:
   - Remnawave `update_subscription()` меняет план/период (expires_at сбрасывается от now)
   - Старая подписка (`upgrade_from`) → `status='cancelled'`
   - Новая → `status='paid'`

## Поля модели

`Subscription.upgrade_from` (FK self, SET_NULL) — ссылка на заменённую подписку.

## Корнер-кейсы

- **Тот же план + тот же период**: `UpgradePreview` возвращает 400 "Вы уже на этом тарифе"
- **Trial (period=0)**: remaining_days считается от `expires_at - now`, `total_days = 90` (placeholder), current_credit ≈ 0 — charge_amount = full new_total
- **`is_upgrade && charge_amount == 0`**: возвращает 400 "Нечего оплачивать"
- **Frontend (Purchase.jsx)**: если `activeSub && !upgradePreview` — показывает "Вы уже на тарифе X" (нельзя купить то же самое)

## UI Flow

```
activeSub existed?
├─ Нет → показать обычные plan cards + "Оплатить"
└─ Да:
   ├─ Выбран тот же plan+period → "Вы уже на тарифе X"
   ├─ Выбран upgrade → upgrade-banner с "Зачёт остатка: XX₽, К оплате: YY₽"
   └─ Выбран downgrade → upgradePreview=null → нет upgrade-banner, 
      показывается regular summary (но кликнуть Оплатить → regular purchase,
      не upgrade — т.е. пользователь может купить Standard после Max как отдельную подписку, после окончания Max)
```

## См. также

- [[Subscription Lifecycle]] — процесс purchase и upgrade
- [[Payment Processing]] — create_*_invoice
- [[Remnawave Integration]] — update_subscription при смене плана
- [[Subscription Model]] — upgrade_from FK
