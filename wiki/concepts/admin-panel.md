---
title: Admin Panel
type: concept
status: stable
created: 2026-04-17
updated: 2026-04-17
tags: [concept, admin, architecture]
---

# Admin Panel

Full-featured админ-панель: бэкенд `admin_api/` + фронтенд `pages/admin/*`. 15 страниц, 30+ API endpoints.

## Архитектура

```
Frontend (React) ─── JWT ──→ Backend (Django)
  /admin/*                    /api/admin/*
  AdminRoute guard            IsAdminUser permission
```

**Двойная защита:**
1. Фронт: `AdminRoute` проверяет `user.is_staff` (из `/api/auth/me/`)
2. Бэк: `IsAdminUser` на каждом endpoint

## Страницы фронтенда

| Путь | Компонент | Backend |
|------|-----------|---------|
| `/admin` | Dashboard.jsx | stats, charts, activity-feed, expiring |
| `/admin/users` | Users.jsx | users list + filters |
| `/admin/users/:id` | UserDetail.jsx | user detail + timeline + remnawave + extend |
| `/admin/subscriptions` | Subscriptions.jsx | subscriptions list + manage |
| `/admin/payments` | Payments.jsx | paid subscriptions (payments view) |
| `/admin/referrals` | Referrals.jsx | Referral records |
| `/admin/analytics` | Analytics.jsx | cohorts, funnel, forecast |
| `/admin/notifications` | Notifications.jsx | bulk send + history |
| `/admin/promo` | Promo.jsx | promo code CRUD |
| `/admin/audit` | Audit.jsx | in-memory audit log |
| `/admin/system` | System.jsx | health checks |
| `/admin/support` | Support.jsx | tickets list + reply |
| `/admin/settings` | Settings.jsx | maintenance toggle + app settings |
| `/admin/export` | Export.jsx | data export |
| `/admin/pricing` | Pricing.jsx | view plans pricing |

## Ключевые особенности Dashboard

**StatsView response (2026-04-17 refactor):**
```json
{
  "users": {"total": 712, "today": 0, "with_telegram": 704},
  "subscriptions": {"active": 66, "expired": 0, "pending": 10, "by_plan": {"max": 53, ...}},
  "revenue": {"total": 3205.0, "month": 3205.0, "avg_check": 30.0},
  "referrals": {"active_referrers": 0, "total_referred": 27}
}
```

Старый flat-keys формат (`total_users`, `active_subscriptions`, `total_revenue`) сохранён для backward compat.

## Runtime observability

| Источник | Где смотреть |
|----------|--------------|
| Django logs | `journalctl -u eifavpn-prod -f` |
| Nginx errors | `/var/log/nginx/error.log` |
| HAR trace | Браузер DevTools → Network → Save HAR |
| Health check | `GET /api/admin/system/health/` (DB, Remnawave, Email) |

## In-memory state warning

Следующие объекты живут в памяти worker-процесса (не shared, теряются при рестарте):

- `_audit_log` — последние 500 admin actions
- `_notification_history` — отправленные bulk notifications
- `_app_settings` — maintenance_mode, motd, и т.д.

Для production требуется миграция в БД или Redis. Сейчас приемлемо для MVP.

## Security

- **IsAdminUser** на 99% endpoints
- **TicketWebhookView** — единственный public endpoint, защищён `X-Webhook-Secret` header (fail-closed в production)
- **Audit log** — каждое destructive action (`delete_promo`, `extend_subscription`, `cancel_subscription`, `update_user`) логируется через `_log_admin_action()`
- **Input validation** — type coercion для BooleanField (string "true" → bool), try/except на int() parse

## Performance optimizations (2026-04-17)

| Проблема | Фикс |
|----------|------|
| N+1 в `TicketListView` (2 запроса/тикет) | `annotate(_msg_count)` + DISTINCT ON для last_message → 3 запроса total |
| 5 отдельных COUNT в `TicketStatsView` | Один `aggregate()` с Count(filter=Q(...)) |
| CohortAnalysisView — 36 запросов в цикле | Одна query с TruncWeek annotate |
| Chart views unbounded `days` | `min(max(int(days), 1), 365)` |

## См. также

- [[Admin API App]] — детали всех endpoints
- [[Support Tickets]] — система тикетов
- [[Security Review]] — IsAdminUser, fail-closed webhooks
- [[JWT Authentication]] — как фронт получает is_staff в `/auth/me/`
