---
title: Proxy System
type: concept
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [concept, proxy, security]
---

# Proxy System

Secure gateway к [[Remnawave]] API через `/api/proxy/<path>`.

## Архитектура

```
Frontend ──JWT──▶ Proxy ──Bearer Token──▶ Remnawave API
                   │
                   ├─ Whitelist check
                   ├─ JWT auth check
                   ├─ Ownership validation
                   └─ Body filtering
```

## Endpoint Whitelist

### Public (без auth)
- `/system/stats` — статистика системы

### Authenticated (JWT required)
- `/users/` — управление пользователями
- `/hwid-user-devices/` — устройства
- `/nodes` — VPN-серверы
- `/hosts` — хосты
- `/internal-squads` — сквады

## Security Layers

### 1. Whitelist
Любой endpoint не из списка → `403 Endpoint not allowed`

### 2. JWT Authentication
Для не-public: `get_user_from_jwt(request)` → `401 Authentication required`

### 3. Ownership Validation
Для `/users/`:
- Разрешено: `/users/by-*`, `/users/{own_uuid}`
- Запрещено: `/users/{other_uuid}` → `403 Access denied`

### 4. Body Filtering (PATCH /users)
Только безопасные поля: `{uuid, email, telegramId, description}`
- UUID обязателен
- UUID должен совпадать с `user.remnawave_uuid`
- Иначе: `403 Can only modify own profile`

## Forwarding

```python
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {REMNAWAVE_BEARER_TOKEN}',
}
url = f'{REMNAWAVE_API_URL}{endpoint}'
# Timeout: 15s
```

Response passthrough: status code + body от Remnawave.

## Ошибки

| Код | Ситуация |
|-----|---------|
| 400 | uuid missing в PATCH body |
| 401 | JWT невалиден |
| 403 | Endpoint не в whitelist / чужой UUID |
| 502 | Remnawave timeout/connection error |

## Файл

`api/views/proxy.py` — ~100 строк

## См. также

- [[Remnawave]] — внешний VPN panel
- [[API App]] — маршрутизация
- [[JWT Authentication]] — валидация токенов в proxy
- [[User Model]] — ownership check через remnawave_uuid
