---
title: User Model
type: entity
app: accounts
file: accounts/models.py
updated: 2026-04-16
---

# User Model

Кастомная модель пользователя, расширяющая `AbstractUser`. Email используется как основной идентификатор.

## Конфигурация

```python
USERNAME_FIELD = 'email'
objects = UserManager()  # кастомный менеджер
```

## Поля

### Core
| Поле | Тип | Unique | Null | Default | Описание |
|------|-----|--------|------|---------|----------|
| email | EmailField | Yes | No | — | Основной идентификатор |
| first_name | CharField | No | No | '' | Имя (из AbstractUser) |

### OAuth
| Поле | Тип | Unique | Null | Default | Описание |
|------|-----|--------|------|---------|----------|
| telegram_id | BigIntegerField | Yes | Yes | NULL | Telegram user ID |
| google_id | CharField(255) | Yes | Yes | NULL | Google OAuth ID |
| avatar_url | URLField | No | No | '' | URL аватара |

### Remnawave
| Поле | Тип | Unique | Null | Default | Описание |
|------|-----|--------|------|---------|----------|
| remnawave_uuid | UUIDField | No | Yes | NULL | UUID в [[Remnawave]] |
| remnawave_short_uuid | CharField(64) | No | No | '' | Короткий UUID |
| subscription_url | URLField | No | No | '' | URL подписки VPN |

### Referral
| Поле | Тип | Unique | Null | Default | Описание |
|------|-----|--------|------|---------|----------|
| referral_code | CharField(16) | Yes | No | auto-gen | 8 символов (A-Z, 0-9) |
| referred_by | FK(self) | No | Yes | NULL | Кто пригласил |
| referral_bonus_days | IntegerField | No | No | 0 | Накопленные бонусные дни |

### Trial/Verification
| Поле | Тип | Default | Описание |
|------|-----|---------|----------|
| used_trial | BooleanField | False | Использован 3-дневный триал |
| used_trial_upgrade | BooleanField | False | Использовано предложение 1₽ |
| email_verified | BooleanField | False | Email подтверждён |

## UserManager

```python
create_user(email, password=None, **extra_fields)
```
- Нормализует email (lowercase)
- Генерирует username из email prefix
- Password опционален (для OAuth users)
- Автогенерация referral_code

```python
create_superuser(email, password, **extra_fields)
```
- is_staff=True, is_superuser=True

## Генерация referral_code

`generate_referral_code()` — 8 символов из `string.ascii_uppercase + string.digits`.
Пример: `"ABC12345"`. Unique constraint предотвращает коллизии.

## Шаблоны email для OAuth users

- Telegram: `tg_{telegram_id}@eifavpn.ru`
- Помечается как неверифицированный
- Можно позже привязать реальный email через [[Accounts App|LinkEmailView]]

## Связи

- `referred_by` → self (реферальное дерево)
- `subscriptions` ← [[Subscription Model]] (related_name='subscriptions')
- `referral_rewards` ← [[Referral Model]] (related_name='referral_rewards')

## См. также

- [[Accounts App]] — views и serializers
- [[Authentication Flows]] — как User создаётся/авторизуется
- [[Referral System]] — реферальная логика
