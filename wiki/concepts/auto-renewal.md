---
title: Auto-Renewal
type: concept
status: stable
created: 2026-04-17
updated: 2026-04-17
tags: [concept, payment, subscription, retention]
---

# Auto-Renewal

Проактивная отправка invoice-ссылки в Telegram за 1 день до истечения подписки. **Не настоящая авто-оплата** (Stars/CryptoPay/Wata не поддерживают recurring), но one-click UX.

## User fields (User model)

| Поле | Тип | Назначение |
|------|-----|-----------|
| `auto_renew` | Boolean, default=False | Включено ли авто-продление |
| `preferred_payment_method` | CharField, blank | stars / crypto / wata (из последней покупки) |
| `preferred_crypto_asset` | CharField, default='USDT' | USDT / TON / BTC |
| `notification_prefs` | JSONField, default=dict | Per-category флаги |

## Cron flow

`subscriptions/renewal.py`:

```python
def run_auto_renewal():
    # 1. Найти пользователей с auto_renew=True
    # 2. У которых активная подписка истекает в ближайшие 1 день (не 0 — чтобы успеть заплатить)
    # 3. Для каждого:
    #    - Создать pending Subscription (такой же план/период как текущий)
    #    - Через create_*_invoice() сгенерировать payment_url
    #    - Отправить Telegram-сообщение с inline-кнопкой "Оплатить"
```

Запускается из management command `run_notifications` (ежедневно через systemd timer):

```bash
python manage.py run_notifications
```

Вызывает:
- `subscriptions.notifications.run_subscription_notifications()` — 3day/1day/expired предупреждения
- `subscriptions.renewal.run_auto_renewal()` — для auto_renew пользователей

## Notification preferences

Пользователь может отключить каждый тип уведомлений через Settings page:

| Ключ | Блокирует |
|------|-----------|
| `purchase` | notify_purchase_success |
| `expiring` | notify_expiring (3day/1day) |
| `expired` | notify_expired |
| `promo` | notify_expired_with_promo |
| `renewal` | notify_renewal_available (auto-renewal invoices) |

Helper `should_notify(user, type)` проверяет `user.notification_prefs.get(type, True)` (backward-compat: dict пустой → все включены).

## UI

Settings.jsx — toggle "Авто-продление" + выбор метода оплаты (Stars/Crypto/Card). Отдельный блок "Уведомления" с 5 переключателями.

## Миграция

`accounts/migrations/0005_user_renewal_notif_prefs.py` — добавляет 4 поля к User и `upgrade_from` FK к Subscription.

## Ограничения

- **Не recurring**: пользователь получает ссылку, но должен вручную оплатить
- **Multi-worker safe**: generate_renewal_invoice использует `Subscription.status='pending'` + select_for_update в process_payment_success
- **Idempotent**: duplicate cron runs безопасны (проверка `Subscription.filter(user, payment_method=method, status='pending', created_at__gte=today).exists()`)

## См. также

- [[Subscription Lifecycle]] — процесс renewal в контексте lifecycle
- [[Payment Processing]] — create_*_invoice функции
- [[Telegram Bot Integration]] — notify_renewal_available
- [[User Model]] — auto_renew field
