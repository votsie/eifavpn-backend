---
title: Wata H2H
type: entity
category: external-service
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [entity, external-service, payment]
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

### Верификация (реализовано 2026-04-16)

Server-to-server проверка: после получения webhook, бэкенд вызывает Wata API (`GET /h2h/links/{id}`) для подтверждения `transactionStatus=Paid` и совпадения суммы. Fail-closed: при недоступности API платёж отклоняется.

См. [[Security Review]] — P0 fix.

## Конвертация

Прямая оплата в RUB, без конвертации.

## См. также

- [[Payment Processing]] — общий flow
- [[Subscription Lifecycle]] — webhook обработка
- [[Security Review]] — аудит безопасности
