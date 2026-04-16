---
title: CryptoPay
type: entity
category: external-service
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [entity, external-service, payment]
---

# CryptoPay

Криптовалютный платёжный шлюз (pay.crypt.bot).

## API

- **Base URL**: `https://pay.crypt.bot/api`
- **Auth header**: `Crypto-Pay-API-Token: {CRYPTOPAY_TOKEN}`
- **User-Agent**: `EIFAVPN/1.0`

## Создание invoice

### POST /createInvoice

**Конкретный ассет:**
```json
{
    "currency_type": "crypto",
    "asset": "USDT" | "TON",
    "amount": "1.65",
    "description": "EIFAVPN Standard — 1 мес",
    "payload": "{\"sub_id\": 123}",
    "expires_in": 3600,
    "paid_btn_name": "callback",
    "paid_btn_url": "https://app.com/cabinet/overview"
}
```

**Fiat fallback:**
```json
{
    "currency_type": "fiat",
    "fiat": "RUB",
    "amount": "207",
    "accepted_assets": "USDT,TON,BTC"
}
```

**Response:**
```json
{
    "ok": true,
    "result": {
        "invoice_id": 123456,
        "bot_invoice_url": "https://t.me/CryptoBot/invoice?...",
        "mini_app_invoice_url": "https://..."
    }
}
```

## Webhook

**Endpoint**: POST `/api/subscriptions/webhook/crypto/`

### Верификация подписи
```python
secret = sha256(CRYPTOPAY_TOKEN)
expected = hmac_sha256(secret, request.body)
assert headers['crypto-pay-api-signature'] == expected
```

### Обработка
- Фильтр: `update_type == 'invoice_paid'`
- Extract sub_id из payload
- `process_payment_success(sub)`

## Конвертация

RUB → Crypto с 3% markup:
```python
crypto_amount = rub_to_crypto(amount_rub, asset)  # + 3% markup
```

## Поддерживаемые валюты

- USDT
- TON
- BTC

## См. также

- [[Payment Processing]] — общий flow
- [[Subscription Lifecycle]] — webhook обработка
