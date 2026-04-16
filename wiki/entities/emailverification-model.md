---
title: EmailVerification Model
type: entity
app: accounts
file: accounts/models.py
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [entity, model, auth]
---

# EmailVerification Model

Хранит 6-значные коды верификации email.

## Поля

| Поле | Тип | Описание |
|------|-----|----------|
| email | EmailField | Email для верификации (не unique) |
| code | CharField(6) | 6-значный числовой код |
| created_at | DateTimeField | auto_now_add |
| used | BooleanField | Помечается True после использования |

## Методы

- `generate_code()` (static) — генерирует случайный 6-значный код
- `is_expired()` — True если `created_at` > 10 минут назад

## Жизненный цикл

1. Создание: SendCodeView или LinkEmailView
2. Использование: VerifyCodeView или LinkEmailVerifyView помечает `used=True`
3. Естественное истечение: >10 мин = `is_expired()`

## Rate Limiting

Один код в минуту на email (проверяется в view, не в модели):
```python
EmailVerification.objects.filter(
    email=email, created_at__gte=now() - timedelta(minutes=1)
).exists()
```

## Ordering

`-created_at` — newest first (для поиска последнего кода).

## См. также

- [[Authentication Flows]] — passwordless flow
- [[Accounts App]] — SendCodeView, VerifyCodeView
