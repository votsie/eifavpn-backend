---
title: Payment Processing
type: concept
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [concept, payment, webhook]
---

# Payment Processing

Три платёжных метода: [[Telegram Stars]], [[CryptoPay]], [[Wata H2H]].

## Общий Flow

```
1. PurchaseView создаёт Subscription(status='pending')
2. Вызывает create_*_invoice() для нужного метода
3. Возвращает {payment_url, payment_id} клиенту
4. Клиент оплачивает через payment_url
5. Платёжная система шлёт webhook
6. process_payment_success(sub) активирует подписку
```

## Telegram Stars

### Создание invoice
```
POST https://api.telegram.org/bot{TOKEN}/createInvoiceLink
{
    title: "EIFAVPN {plan} — {period} мес",
    description: "VPN подписка...",
    payload: '{"sub_id": 123}',
    currency: "XTR",
    prices: [{label: "VPN подписка", amount: stars_count}]
}
```

### Конвертация
RUB → USDT (по курсу) → Stars (50 stars ≈ $0.75 + 15% markup)

### Webhook: POST `/webhook/stars/`
- `pre_checkout_query` → всегда approve
- `successful_payment` → extract sub_id из payload → process_payment_success()
- `/start` команда → send_welcome()

## CryptoPay

### Создание invoice
```
POST https://pay.crypt.bot/api/createInvoice
Headers: {Crypto-Pay-API-Token: token}
```

**Конкретный ассет (USDT/TON):**
```json
{
    "currency_type": "crypto",
    "asset": "USDT",
    "amount": "1.65",
    "payload": "{\"sub_id\": 123}",
    "expires_in": 3600
}
```

**Fiat RUB:**
```json
{
    "currency_type": "fiat",
    "fiat": "RUB",
    "amount": "207",
    "accepted_assets": "USDT,TON,BTC"
}
```

### Конвертация
RUB → Crypto + 3% markup

### Webhook: POST `/webhook/crypto/`
**Верификация**: HMAC-SHA256
```python
secret = sha256(CRYPTOPAY_TOKEN)
expected = hmac_sha256(secret, request.body)
assert request.headers['crypto-pay-api-signature'] == expected
```
Фильтр: `update_type == 'invoice_paid'`

## Wata H2H

### Создание invoice
```
POST https://api.wata.pro/api/h2h/links/
Headers: {Authorization: Bearer {token}}
{
    "amount": 207.00,
    "currency": "RUB",
    "orderId": "eifavpn_123",
    "successRedirectUrl": ".../cabinet/overview",
    "failRedirectUrl": ".../cabinet/purchase?failed=1"
}
```

### Webhook: POST `/webhook/wata/`
- Проверка: `transactionStatus == 'Paid'`
- Parse orderId: `eifavpn_{sub_id}`

> [!gap] Security Note
> Wata webhook не имеет проверки подписи в текущем коде.

## Сравнение методов

| Метод | Валюта | Markup | Верификация webhook |
|-------|--------|--------|-------------------|
| Stars | XTR (Stars) | ~15% | Telegram Bot API |
| CryptoPay | USDT/TON/BTC | 3% | HMAC-SHA256 |
| Wata | RUB | 0% | Нет подписи |

## См. также

- [[Subscription Lifecycle]] — process_payment_success
- [[Telegram Stars]] — детали Stars
- [[CryptoPay]] — детали CryptoPay
- [[Wata H2H]] — детали Wata
