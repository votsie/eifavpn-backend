---
title: Referral Model
type: entity
app: accounts
file: accounts/models.py
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [entity, model, referral]
---

# Referral Model

Запись о реферальной связи между пользователями.

## Поля

| Поле | Тип | Описание |
|------|-----|----------|
| referrer | FK(User, CASCADE) | Пригласивший (related_name='referral_rewards') |
| referred | FK(User, CASCADE) | Приглашённый (related_name='referred_by_record') |
| subscription | FK(Subscription, SET_NULL) | Подписка, активировавшая бонус |
| bonus_applied | BooleanField | Бонус выдан (default=False) |
| created_at | DateTimeField | auto_now_add |

## Бизнес-логика

Referral создаётся в `process_payment_success()` при первой оплате приглашённого пользователя:

1. Проверка: `user.referred_by` существует
2. Проверка: нет записи с `bonus_applied=True` для этого referred
3. Если referrer имеет `remnawave_uuid`:
   - `extend_subscription(referrer.remnawave_uuid, 7 дней)`
   - `referrer.referral_bonus_days += 7`
4. Создание Referral с `bonus_applied=True`

## Защита от дублирования

Бонус выдаётся ровно 1 раз на реферала. Проверка:
```python
Referral.objects.filter(referred=user, bonus_applied=True).exists()
```

## См. также

- [[Referral System]] — полная логика
- [[User Model]] — поле referred_by
- [[Subscription Lifecycle]] — когда создаётся Referral
