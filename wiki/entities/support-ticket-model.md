---
title: SupportTicket Model
type: entity
app: accounts
file: accounts/models.py
status: stable
created: 2026-04-17
updated: 2026-04-17
tags: [entity, model, support]
---

# SupportTicket Model

Тикет поддержки — обращение пользователя с диалогом (`TicketMessage`).

## Поля

### SupportTicket
| Поле | Тип | Описание |
|------|-----|----------|
| `user` | FK(User, CASCADE) | Автор тикета |
| `subject` | CharField(255) | Тема (авто из первого сообщения, первые 100 символов) |
| `category` | CharField | connection / payment / account / speed / feature / other |
| `priority` | CharField | low / normal / high / urgent |
| `status` | CharField | open / in_progress / waiting / resolved / closed |
| `assigned_to` | FK(User, SET_NULL) | Админ, назначенный на тикет |
| `telegram_chat_id` | BigInteger | Чат в Telegram откуда пришёл тикет |
| `created_at` / `updated_at` | DateTime | auto_now_add / auto_now |

**Meta:** `ordering = ['-updated_at']`

### TicketMessage
| Поле | Тип | Описание |
|------|-----|----------|
| `ticket` | FK(SupportTicket, CASCADE, related_name='messages') | |
| `sender` | FK(User, SET_NULL) | null для системных сообщений |
| `is_staff` | Boolean | True = ответ админа |
| `text` | TextField | |
| `telegram_message_id` | BigInteger | ID отправленного сообщения в TG (для edit/delete) |
| `created_at` | DateTime | |

## Flow создания

1. Пользователь пишет боту в Telegram
2. Бот отправляет `POST /api/admin/tickets/webhook/` с payload:
   ```json
   {
     "telegram_id": 12345,
     "chat_id": 12345,
     "message_id": 67890,
     "text": "Не могу подключиться",
     "category": "connection"
   }
   ```
3. Webhook проверяет `X-Webhook-Secret` header против `TELEGRAM_WEBHOOK_SECRET`
4. Если у пользователя есть открытый тикет (status in open/in_progress/waiting) → добавляет сообщение к нему и меняет status на 'open'
5. Иначе создаёт новый SupportTicket + TicketMessage

## Flow ответа

1. Админ открывает [[Admin Panel]] → Support → тикет
2. Пишет ответ → `POST /admin/tickets/{pk}/reply/`
3. Бэкенд:
   - Создаёт TicketMessage с `is_staff=True`, `sender=admin`
   - Авто-status: если был 'open' → 'in_progress'
   - Авто-assign: если не назначен → назначается на текущего админа
   - Отправляет HTML-сообщение в Telegram с цитированием темы тикета
   - Сохраняет `telegram_message_id` в TicketMessage

## Запросы (N+1 fix 2026-04-17)

Раньше `serialize_ticket(t)` делал 2 доп. запроса на каждый тикет (count + last_message). Исправлено:
- `annotate(_msg_count=Count('messages'))` — message_count в главном запросе
- `DISTINCT ON (ticket_id)` — last_message в 1 batch-запросе для всей страницы

Теперь 20 тикетов = 3 SQL запроса вместо 41.

## См. также

- [[Admin API App]] — Ticket endpoints
- [[Telegram Bot Integration]] — webhook и ответы
- [[User Model]] — FK assigned_to, sender
