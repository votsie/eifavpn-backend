---
title: Wata H2H
type: entity
category: external-service
updated: 2026-04-16
---

# Wata H2H

Платёжный шлюз для российских карт и СБП.

## API

- **Base URL**: `https://api.wata.pro/api`
- **Auth**: `Authorization: Bearer {WATA_TOKEN}`
- **User-Agent**: `EIFAVPN/1.0`

## Создание платёжной ссылки

### POST /h2h/links/

```json
{
    "amount": 207.00,
    "currency": "RUB",
    "orderId": "eifavpn_123",
    "description": "EIFAVPN Standard — 1 мес",
    "successRedirectUrl": "https://app.com/cabinet/overview",
    "failRedirectUrl": "https://app.com/cabinet/purchase?failed=1"
}
```

**Response:**
```json
{
    "id": "wata_payment_789",
    "url": "https://wata.pro/pay/xyz123",
    "status": "active"
}
```

## Webhook

**Endpoint**: POST `/api/subscriptions/webhook/wata/`

**Payload:**
```json
{
    "orderId": "eifavpn_123",
    "transactionStatus": "Paid",
    "transactionId": "tx_789",
    "amount": 207.00
}
```

**Обработка:**
1. Проверка: `transactionStatus == 'Paid'`
2. Parse orderId: `eifavpn_{sub_id}`
3. `process_payment_success(sub)`

> [!gap] Security Note
> В текущем коде нет проверки подписи webhook-запроса от Wata.

## Конвертация

Прямая оплата в RUB, без конвертации.

## См. также

- [[Payment Processing]] — общий flow
- [[Subscription Lifecycle]] — webhook обработка
