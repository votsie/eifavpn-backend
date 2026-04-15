---
title: Referral System
type: concept
updated: 2026-04-16
---

# Referral System

Двусторонняя реферальная система: скидка рефералу + бонусные дни реферреру.

## Параметры

- **Скидка рефералу**: 10% от стоимости подписки
- **Бонус реферреру**: +7 дней к подписке
- **Реферальный код**: 8 символов (A-Z, 0-9), уникальный

## Flow

```
Referrer                    Referred                  Backend
  │                            │                         │
  │─GET /referral/my/──────────┤                         │
  │◀─{code: "ABC12345",       │                         │
  │   link: ".../ref=ABC12345"}│                         │
  │                            │                         │
  │──Share link────────────────▶                         │
  │                            │                         │
  │                            │─Register with ref code──▶
  │                            │  (verify-code/register)  │
  │                            │                         │─user.referred_by = referrer
  │                            │                         │
  │                            │─Purchase subscription───▶
  │                            │                         │─Price: base × 0.9 (10% off)
  │                            │                         │
  │                            │─Payment webhook─────────▶
  │                            │                         │─process_payment_success()
  │                            │                         │  ├─extend referrer +7 days
  │                            │                         │  ├─referrer.bonus_days += 7
  │                            │                         │  └─Referral(bonus_applied=True)
  │                            │                         │
  │◀──Telegram: "+7 дней!"────│                         │
```

## Компоненты

### 1. Генерация кода
- `generate_referral_code()` в `accounts/models.py`
- Создаётся при регистрации пользователя
- 8 символов: `random.choices(string.ascii_uppercase + string.digits, k=8)`

### 2. Реферальная ссылка
- Формат: `{APP_URL}/register?ref={referral_code}`
- Default APP_URL: `https://eifavpn.ru`

### 3. Привязка реферала
- При регистрации (VerifyCodeView/RegisterSerializer):
  ```python
  if referral_code:
      referrer = User.objects.get(referral_code=referral_code)
      user.referred_by = referrer
  ```

### 4. Скидка 10%
- В PurchaseView:
  ```python
  if user.referred_by:
      discount = base_price * REFERRAL_DISCOUNT_PERCENT / 100
      price -= discount
  ```

### 5. Бонус +7 дней
- В `process_payment_success()`:
  - Проверка: `not Referral.objects.filter(referred=user, bonus_applied=True).exists()`
  - `remnawave.extend_subscription(referrer.uuid, 7)`
  - Создание Referral записи

### 6. Telegram Sharing
- PrepareShareView: `savePreparedInlineMessage` через Telegram Bot API
- Сообщение с реферальной ссылкой для шаринга в чатах

## API

| Endpoint | Описание |
|----------|----------|
| GET `/api/referral/my/` | Код, ссылка, total_referrals, bonus_days |
| GET `/api/referral/list/` | Список рефералов (masked emails + subscribed flag) |
| POST `/api/auth/prepare-share/` | Telegram inline sharing |

## Модели

- [[User Model]]: `referral_code`, `referred_by`, `referral_bonus_days`
- [[Referral Model]]: `referrer`, `referred`, `subscription`, `bonus_applied`

## См. также

- [[Subscription Lifecycle]] — когда применяется бонус
- [[Accounts App]] — ReferralMyView, ReferralListView
