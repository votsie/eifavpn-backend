---
title: Telegram Bot Integration
type: entity
category: external-service
updated: 2026-04-16
---

# Telegram Bot Integration

Использование Telegram Bot API для уведомлений, платежей и шаринга.

## Конфигурация

- **Token**: `settings.TELEGRAM_BOT_TOKEN`
- **Mini App URL**: `https://t.me/eifavpn_bot/eifavpn`
- **Welcome Sticker**: Закодированный sticker ID

## Функции уведомлений (notifications.py)

### send_welcome(chat_id, first_name)
Приветственное сообщение при /start:
- Стикер + HTML-сообщение
- Inline кнопка "Открыть EIFAVPN"

### notify_purchase_success(user, subscription)
После успешной оплаты:
- Тариф, период, "серверы доступны"
- Кнопка открытия приложения

### notify_expiring(user, days_left)
За 3 дня и 1 день до истечения:
- Напоминание о продлении

### notify_expired(user)
В день истечения:
- "VPN отключён, продлите подписку"

### notify_expired_with_promo(user)
Через 1 день после истечения:
- Генерация персонального промокода (BACK + 5 chars, 10%)
- Одноразовый, только для этого пользователя

### run_subscription_notifications()
Ежедневный cron job:
- Итерация по всем paid подпискам
- Отправка уведомлений на основе days_left

## Inline Sharing

### PrepareShareView (accounts/views.py)
```
POST /api/auth/prepare-share/
→ savePreparedInlineMessage (Bot API)
```

Сообщение для шаринга реферальной ссылки:
```
🔒 EIFAVPN — быстрый и безопасный VPN
Попробуй бесплатно 3 дня MAX!
👉 https://eifavpn.ru/register?ref={code}
```

## Emoji

Используются custom emoji ID (требуют Telegram Premium бота):
- heart, lock, crown, cd, server, gift, handshake, sword

## Helper функции

| Функция | Описание |
|---------|----------|
| `_send_message()` | sendMessage с HTML parse mode |
| `_send_sticker()` | sendSticker (silent fail) |
| `_open_button()` | Inline keyboard → Mini App URL |

## См. также

- [[Telegram Stars]] — Stars платежи
- [[Subscriptions App]] — уведомления
- [[Referral System]] — inline sharing
