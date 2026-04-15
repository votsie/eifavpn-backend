---
title: JWT Authentication
type: concept
updated: 2026-04-16
---

# JWT Authentication

Все API-эндпоинты используют JWT (JSON Web Tokens) через `djangorestframework-simplejwt`.

## Конфигурация

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=90),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

## Токены

| Тип | Время жизни | Назначение |
|-----|------------|-----------|
| Access | 1 день | Авторизация API-запросов |
| Refresh | 90 дней | Получение нового access token |

## Использование

### Заголовок
```
Authorization: Bearer <access_token>
```

### Получение токенов
Все auth-эндпоинты возвращают пару:
```json
{
    "tokens": {
        "access": "<JWT>",
        "refresh": "<JWT>"
    }
}
```

### Обновление
```
POST /api/auth/refresh/ {refresh: "<token>"}
→ {access: "<new_token>", refresh: "<new_refresh>"}
```

### Отзыв (logout)
```
POST /api/auth/logout/ {refresh: "<token>"}
→ Refresh token добавляется в blacklist
```

## Token Rotation

При каждом refresh:
1. Выдаётся новый access + новый refresh
2. Старый refresh автоматически blacklist-ится
3. Это предотвращает повторное использование украденных refresh-токенов

## Генерация

```python
from rest_framework_simplejwt.tokens import RefreshToken

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }
```

## Зависимости

- `rest_framework_simplejwt` — основная библиотека
- `rest_framework_simplejwt.token_blacklist` — app для blacklist таблицы

## См. также

- [[Authentication Flows]] — где генерируются токены
- [[Project Settings]] — конфигурация
- [[Proxy System]] — JWT валидация в proxy
