---
title: Support Tickets
type: concept
status: stable
created: 2026-04-17
updated: 2026-04-17
tags: [concept, support, telegram]
---

# Support Tickets

Система тикетов поддержки с Telegram-интеграцией. Bot принимает сообщения от пользователей, админы отвечают через `/admin/support`, ответ возвращается в Telegram.

## Архитектура

```
User in Telegram         EIFAVPN Bot          Backend                 Admin UI
      │                      │                   │                        │
      │ "Не работает VPN"    │                   │                        │
      ├─────────────────────→│                   │                        │
      │                      │ POST /admin/      │                        │
      │                      │ tickets/webhook/  │                        │
      │                      ├──────────────────→│                        │
      │                      │                   │ Create SupportTicket + │
      │                      │                   │ TicketMessage          │
      │                      │                   │                        │
      │                      │                   │ GET /admin/tickets/    │
      │                      │                   │←───────────────────────┤
      │                      │                   │                        │
      │                      │                   │ POST /admin/tickets/   │
      │                      │                   │      {id}/reply/       │
      │                      │                   │←───────────────────────┤
      │                      │ sendMessage       │                        │
      │                      │←──────────────────┤                        │
      │ "Ответ по тикету..."  │                   │                        │
      │←─────────────────────┤                   │                        │
```

## Модели

См. [[SupportTicket Model]] для полной спецификации полей.

- **SupportTicket** — тикет (subject, category, priority, status, assigned_to)
- **TicketMessage** — сообщение в тикете (text, is_staff, telegram_message_id)

## Jobs ↔ Users

Один пользователь может иметь только **один активный тикет одновременно**. Новое сообщение от того же пользователя:
- Если есть тикет в status in `[open, in_progress, waiting]` → добавляется сообщение к нему, status → 'open'
- Иначе создаётся новый тикет

Это убирает дубликаты и упрощает диалог.

## Auto-assignment

Первый админ, ответивший на тикет, становится `assigned_to`. Остальные видят кто занимается.

## Статусы

| Status | Когда устанавливается |
|--------|----------------------|
| `open` | Новый тикет / пользователь написал снова после waiting |
| `in_progress` | Админ ответил (автоматически из open) |
| `waiting` | Админ вручную поставил (ждём ответа от пользователя) |
| `resolved` | Админ пометил решённым через кнопку "Отправить и решить" |
| `closed` | Архивный статус, больше не показывается |

## Webhook security

Bot шлёт:
```http
POST /api/admin/tickets/webhook/
X-Webhook-Secret: <TELEGRAM_WEBHOOK_SECRET>

{
  "telegram_id": 12345,
  "chat_id": 12345,
  "message_id": 67890,
  "text": "...",
  "category": "connection"
}
```

Fail-closed: если `TELEGRAM_WEBHOOK_SECRET` не задан в production → 500 "Webhook secret not configured".

## UI

`pages/admin/Support.jsx`:
- Stats (открытые, в работе, ожидание, решено сегодня)
- Фильтры: status, priority, category, assigned_to (me/unassigned), search
- Detail view с диалогом, переключение статуса, reply composer
- Кнопка "Отправить и решить" — single-click ответ + close

## Категории

Соответствуют FAQ на фронтенде:
- connection — Проблемы с подключением
- payment — Вопросы оплаты
- account — Проблемы с аккаунтом
- speed — Скорость/качество
- feature — Предложение
- other — Другое

## См. также

- [[SupportTicket Model]] — схема БД
- [[Admin API App]] — все ticket endpoints
- [[Admin Panel]] — UI архитектура
- [[Telegram Bot Integration]] — webhook и ответы
