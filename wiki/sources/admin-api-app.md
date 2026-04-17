---
title: Admin API App
type: source
app: admin_api
status: stable
created: 2026-04-17
updated: 2026-04-17
tags: [source, admin, analytics]
---

# Admin API App

Django-приложение `admin_api/` — отдельный модуль для админ-панели. Все endpoints требуют `IsAdminUser` (user.is_staff=True).

## Файлы

| Файл | Назначение |
|------|-----------|
| `views.py` (~1500 строк) | 32 view-класса: stats, users, subscriptions, payments, analytics, tickets |
| `urls.py` | Все URL под `/api/admin/` |
| `apps.py` | AppConfig |

## Категории endpoints

### 1. Dashboard Stats

| Endpoint | View | Возвращает |
|----------|------|-----------|
| `GET /admin/stats/` | `StatsView` | `{users:{total,today,with_telegram}, subscriptions:{active,expired,pending,by_plan}, revenue:{total,month,avg_check}, referrals:{active_referrers,total_referred}}` |
| `GET /admin/stats/chart/registrations/?days=30` | `RegistrationChartView` | Array `[{date, count}]` за N дней |
| `GET /admin/stats/chart/revenue/?days=30` | `RevenueChartView` | Array `[{date, total, count}]` — сумма в RUB за день |
| `GET /admin/stats/activity-feed/?limit=20` | `ActivityFeedView` | Последние события (registrations/payments/trials), объединённые по timestamp |
| `GET /admin/stats/expiring/` | `ExpiringSubsView` | Подписки, истекающие в течение 7 дней |

### 2. Users

| Endpoint | View | Описание |
|----------|------|----------|
| `GET /admin/users/` | `UserListView` | Список + фильтры: search, plan (standard/pro/max/none), status (active/expired/trial/never) |
| `GET /admin/users/{pk}/` | `UserDetailView` | Детали + active_subscription + total_paid + subscription_count |
| `PATCH /admin/users/{pk}/` | `UserDetailView.patch` | is_staff, is_active, email_verified, used_trial — с coerce string→bool |
| `POST /admin/users/{pk}/extend/` | `UserExtendView` | Продлить подписку на N дней (1-365) через Remnawave |
| `GET /admin/users/{pk}/timeline/` | `UserTimelineView` | Хронология: регистрация + subscriptions + referrals |
| `GET /admin/users/{pk}/remnawave/` | `UserRemnawaveView` | Данные из Remnawave (traffic, devices, expiry) |

### 3. Subscriptions & Payments

| Endpoint | View | Описание |
|----------|------|----------|
| `GET /admin/subscriptions/?status=&plan=&method=` | `SubscriptionListView` | Фильтруемый список |
| `POST /admin/subscriptions/{pk}/manage/` | `SubscriptionManageView` | Actions: `cancel`, `extend`, `change_status` |
| `GET /admin/payments/?method=` | `PaymentListView` | Только status='paid' |
| `GET /admin/referrals/` | `ReferralListView` | Все Referral records (с bonus_applied) |

### 4. Analytics

| Endpoint | View | Описание |
|----------|------|----------|
| `GET /admin/analytics/cohorts/?weeks=12` | `CohortAnalysisView` | Weekly cohorts: registered → trial → paid. Single annotated query с TruncWeek |
| `GET /admin/analytics/funnel/` | `FunnelView` | Registered → Trial → Paid с conversion rates |
| `GET /admin/analytics/forecast/` | `ForecastView` | Linear forecast на основе последних 30 дней. `growth_percent: null` если prev=0 |

### 5. System & Audit

| Endpoint | View | Описание |
|----------|------|----------|
| `GET /admin/system/health/` | `SystemHealthView` | DB, Remnawave API, Email — статусы |
| `GET /admin/audit/` | `AuditLogView` | In-memory log (до 500) + Django admin LogEntry |
| `GET /admin/maintenance/` / `POST` | `MaintenanceView` | Toggle maintenance mode (in-memory `_app_settings`) |
| `GET /admin/settings/` / `PATCH` | `SettingsView` | App settings (masked secrets) |

### 6. Search & Notifications

| Endpoint | View | Описание |
|----------|------|----------|
| `GET /admin/search/?q=` | `GlobalSearchView` | Поиск по users, subscriptions, promos (min 2 chars) |
| `POST /admin/notifications/send/` | `SendNotificationView` | Bulk TG-рассылка по user_ids |
| `GET /admin/notifications/history/` | `NotificationHistoryView` | In-memory история |

### 7. Promo Codes

| Endpoint | View | Описание |
|----------|------|----------|
| `GET/POST /admin/promo/` | `PromoListCreateView` | Список + создание (graceful при PromoCode=None) |
| `PATCH/DELETE /admin/promo/{pk}/` | `PromoDetailView` | Редактирование (`valid_until`, `is_active`, и т.д.) |
| `POST /admin/bulk/extend/` | `BulkExtendView` | Массовое продление для N user_ids |

### 8. Support Tickets

См. [[Support Tickets]] для полной документации.

| Endpoint | View |
|----------|------|
| `GET /admin/tickets/` | `TicketListView` (с annotated _msg_count, batched last_messages) |
| `GET /admin/tickets/stats/` | `TicketStatsView` (single aggregate) |
| `POST /admin/tickets/webhook/` | `TicketWebhookView` (public, secret-verified) |
| `GET/PATCH /admin/tickets/{pk}/` | `TicketDetailView` |
| `POST /admin/tickets/{pk}/reply/` | `TicketReplyView` (отправляет в TG) |

## Важные паттерны

### Pagination helper
`paginate_qs(queryset, request)` возвращает `(items, meta_dict)` с `{page, page_size, total, count, total_pages}`. `count` — backward-compat alias для `total`.

### Audit logging
`_log_admin_action(admin_user, action, details)` — in-memory list (max 500). Ротация FIFO. На production нужна модель или Redis.

### Известные ограничения

- **In-memory state**: `_audit_log`, `_notification_history`, `_app_settings`, `_maintenance` — теряются при рестарте gunicorn, не шарятся между workers. Для MVP приемлемо, но для scale нужна миграция в БД/Redis.
- **N+1 в ticket listing** — исправлено 2026-04-17 через `annotate(_msg_count)` + `DISTINCT ON (ticket_id)` для last_message.

## См. также

- [[Support Tickets]] — архитектура тикетов
- [[Admin Panel]] — фронтенд концепт
- [[Security Review]] — IsAdminUser checks, fail-closed webhooks
- [[API Endpoints Reference]] — полный список всех API
