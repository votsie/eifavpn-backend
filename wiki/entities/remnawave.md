---
title: Remnawave
type: entity
category: external-service
updated: 2026-04-16
---

# Remnawave

Внешняя VPN-панель для управления пользователями и подключениями.

## Общая информация

- **URL**: `https://wavepanel.eifastore.ru/api`
- **Auth**: Bearer token (`REMNAWAVE_BEARER_TOKEN`)
- **Протокол**: REST JSON API

## Используемые эндпоинты

### POST /users — Создание подписки
```json
{
    "username": "eifa_{user_id}_{plan}",
    "expireAt": "ISO8601",
    "trafficLimitBytes": 1099511627776,
    "trafficLimitStrategy": "MONTH" | "NO_RESET",
    "hwidDeviceLimit": 3,
    "tag": "EIFA_{user_id}",
    "description": "EIFAVPN {plan} - {email}",
    "activeInternalSquadUuids": ["38d5757f-..."],
    "email": "user@email.com",
    "telegramId": 123456
}
```
Response: `{uuid, shortUuid, subscriptionUrl}`

### PATCH /users — Обновление подписки
```json
{
    "uuid": "...",
    "expireAt": "ISO8601",
    "status": "ACTIVE",
    "trafficLimitBytes": 0,
    "trafficLimitStrategy": "NO_RESET",
    "hwidDeviceLimit": 6,
    "activeInternalSquadUuids": ["..."]
}
```

### GET /users/{uuid} — Данные пользователя
Response включает:
- `status`: ACTIVE/EXPIRED/SUSPENDED
- `userTraffic`: usedTrafficBytes, lifetimeUsedTrafficBytes, onlineAt, firstConnectedAt
- `trafficLimitBytes`, `hwidDeviceLimit`, `expireAt`, `subscriptionUrl`

### PATCH /users (disable) — Отключение при удалении аккаунта
```json
{"uuid": "...", "status": "DISABLED"}
```

## Интеграция в проекте

| Файл | Использование |
|------|--------------|
| `subscriptions/remnawave.py` | API клиент (create, update, extend, get) |
| `subscriptions/views.py` | Trial, purchase, my subscription |
| `accounts/views.py` | DeleteAccountView (disable) |
| `api/views/proxy.py` | Проксирование frontend запросов |

## Функции клиента (remnawave.py)

| Функция | Описание |
|---------|----------|
| `create_subscription(user, plan, period, days)` | POST /users |
| `update_subscription(uuid, plan, period, days)` | PATCH /users |
| `extend_subscription(uuid, days)` | GET /users/{uuid} → PATCH /users |
| `get_user_data(uuid)` | GET /users/{uuid} |

## Squad

Все тарифы используют один DEFAULT_SQUAD: `38d5757f-a45a-4144-b4b3-fd3f5facb5dd`

## Timeout

Все API-вызовы: 10-15 секунд. Ошибки логируются, в некоторых случаях игнорируются (best-effort).

## См. также

- [[Remnawave Integration]] — детали клиента
- [[Proxy System]] — проксирование через backend
- [[Subscription Lifecycle]] — где вызывается
