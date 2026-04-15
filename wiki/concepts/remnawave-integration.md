---
title: Remnawave Integration
type: concept
updated: 2026-04-16
---

# Remnawave Integration

Детали интеграции с [[Remnawave]] VPN-панелью через API-клиент в `subscriptions/remnawave.py`.

## API-клиент

### create_subscription(user, plan, period_months=0, days=None)

Создание нового пользователя VPN:
- Username: `eifa_{user.id}_{plan}`
- Tag: `EIFA_{user.id}`
- Expiry: now + period_months или now + days
- Traffic/devices из PLANS config
- Squad: DEFAULT_SQUAD

**Сохраняет в User:**
- `remnawave_uuid` — основной UUID
- `remnawave_short_uuid` — короткий ID
- `subscription_url` — URL для подключения

### update_subscription(uuid, plan, period_months=0, days=None)

Обновление существующей подписки:
- Новый expiry от текущей даты
- Status → ACTIVE
- Обновление traffic/devices по новому плану

### extend_subscription(uuid, days)

Продление на N дней (сохраняет текущий план):
1. GET текущие данные (expireAt)
2. new_expiry = max(current_expiry, now) + days
3. PATCH с новым expiry + ACTIVE

**Используется для:**
- Promo bonus days
- Referral bonus (+7 дней)
- Gift promo activation

### get_user_data(uuid)

Получение live-данных:
- Traffic usage (used/lifetime)
- Online status
- Device limit
- Subscription URL

## Планы → Remnawave mapping

| Plan | Traffic | Strategy | Devices |
|------|---------|----------|---------|
| Standard | 1 TB | MONTH (reset) | 3 |
| Pro | Unlimited | NO_RESET | 4 |
| Max | Unlimited | NO_RESET | 6 |

## Error Handling

- Все запросы: `raise_for_status()` для 4xx/5xx
- Исключения ловятся в views
- DeleteAccountView: best-effort (игнорирует ошибки)
- Timeout: 10-15 секунд

## Файлы

- `subscriptions/remnawave.py` — клиент (~123 строк)
- `api/views/proxy.py` — [[Proxy System]] для frontend
- `accounts/views.py` — disable при удалении

## См. также

- [[Remnawave]] — описание сервиса
- [[Subscription Lifecycle]] — где вызывается
- [[Proxy System]] — проксирование к Remnawave
