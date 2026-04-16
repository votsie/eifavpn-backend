---
title: Telegram Stars
type: entity
category: external-service
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [entity, external-service, payment]
---

# Telegram Stars

Внутренняя валюта Telegram для оплаты цифровых товаров.

## Создание invoice

### POST /bot{TOKEN}/createInvoiceLink

```json
{
    "title": "EIFAVPN Standard — 1 мес",
    "description": "VPN подписка Standard на 1 мес.",
    "payload": "{\"sub_id\": 123}",
    "currency": "XTR",
    "prices": [
        {"label": "VPN подписка", "amount": 100}
    ]
}
```

**Response:** `{"result": "https://t.me/..."}`

## Конвертация

```
RUB → USDT (по курсу) → Stars
50 Stars ≈ $0.75
+ ~15% markup
```

## Webhook

**Endpoint**: POST `/api/subscriptions/webhook/stars/`
Обрабатывает Telegram Bot API updates.

### Типы updates

1. **pre_checkout_query** — автоматически approve:
   ```python
   answerPreCheckoutQuery(id=query_id, ok=True)
   ```

2. **successful_payment** — подтверждение оплаты:
   ```python
   payload = JSON.parse(successful_payment.invoice_payload)
   sub = Subscription.objects.get(id=payload['sub_id'], status='pending')
   process_payment_success(sub)
   ```

3. **/start command** — приветствие:
   ```python
   send_welcome(chat_id, first_name)
   ```

## См. также

- [[Payment Processing]] — общий flow
- [[Telegram Bot Integration]] — другие Bot API функции
