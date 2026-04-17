---
title: Wiki Log
type: meta
status: developing
created: 2026-04-16
updated: 2026-04-17
tags: [meta, log]
---

# Wiki Log

## 2026-04-17 ingest | HAR analysis + wiki sync with current code

- Source: `C:\Users\aafek\Downloads\eifavpn.ru.har` (184 requests, 169×200, 1×404)
- Runtime fixes:
  - `/api/admin/maintenance/` was 404 → created `MaintenanceView` with GET+POST
  - `active_referrers: 0` was misleading → added `total_referred: 27` (users via ?ref=, not yet paid)
  - `forecast.growth_percent` returns `null` (not 0) when `prev_30d=0` so UI can show "New"
- Wiki pages created:
  - [[Admin API App]] — полная документация `admin_api/` (30+ endpoints)
  - [[SupportTicket Model]] — схема тикетов + TicketMessage
  - [[Auto-Renewal]] — flow проактивных invoice-ссылок + notification_prefs
  - [[Plan Upgrade]] — pro-rata алгоритм + статус "downgrade disabled"
  - [[Admin Panel]] — архитектура фронт/бэк, in-memory warnings, N+1 fixes
  - [[Support Tickets]] — полный flow webhook→admin→reply
- Wiki pages updated:
  - [[User Model]] — добавлены auto_renew/notification_prefs/tickets поля + 0005 миграция
  - [[Subscription Model]] — добавлены `upgrade_from` FK, `error` статус, idempotency note
  - [[index]] — добавлены ссылки на новые pages
- HAR observations (non-bugs):
  - User with plan='max', period=0, expires 10 лет вперёд → trial продлён админом
  - Activity feed show "downgrade" payments → старые записи до отключения downgrade 2026-04-17
- Key insight: После 4 дней интенсивной разработки wiki отставал от кода на 4 новых больших фичи (admin panel, tickets, auto-renewal, upgrade). Синхронизирован по HAR + изменениям.

## 2026-04-16 lint + ingest | Security Audit & Wiki Health Check
- Source: Full code review + wiki lint (33 pages scanned)
- Summary: [[Security Review]], [[Lint Report 2026-04-16]]
- Pages created: [[Security Review]], [[Lint Report 2026-04-16]], [[Dashboard]]
- Pages updated: [[Authentication Flows]], [[Subscription Lifecycle]], [[Payment Processing]], [[Wata H2H]], [[Proxy System]], [[Referral System]], [[overview]], [[hot]], [[index]] + frontmatter on all 33 pages
- Code fixes: 13 issues (3x P0, 5x P1, 5x P2) — JWT fragment transport, Wata webhook verification, HMAC OAuth state, secrets for codes, HSTS/secure cookies, Django admin, expires_at recalc, Stars webhook secret, logging config, is_new flag, .gitignore, .env.example
- Cross-references added: [[Security Review]] linked from 8 pages, [[User Model]]/[[Telegram Bot Integration]]/[[Subscription Model]] cross-linked where missing
- Frontmatter fixed: status, created, tags added to all 33 pages
- Stale claims fixed: Wata "no signature verification" gap → verified
- Key insight: Все 3 webhook-метода теперь верифицированы. OAuth state подписан HMAC. Токены в URL fragments.

## 2026-04-16 ingest | Frontend Cross-References
- Source: Multi-agent scan of eifavpn-frontend project
- Summary: [[EIFAVPN Frontend]]
- Pages created: [[EIFAVPN Frontend]]
- Pages updated: [[overview]], [[hot]], [[index]]
- Key insight: Добавлены кросс-ссылки на фронтенд wiki. Оба проекта теперь связаны через entity pages.

## 2026-04-16 ingest | Full Project Scan
- Source: All project files (accounts/, api/, subscriptions/, eifavpn/, .github/)
- Summary: Complete codebase documentation
- Pages created: [[Accounts App]], [[API App]], [[Subscriptions App]], [[User Model]], [[Subscription Model]], [[Referral Model]], [[EmailVerification Model]], [[PromoCode Model]], [[Authentication Flows]], [[Subscription Lifecycle]], [[Referral System]], [[Promo Code System]], [[Remnawave]], [[Remnawave Integration]], [[CryptoPay]], [[Wata H2H]], [[Telegram Stars]], [[Telegram Bot Integration]], [[JWT Authentication]], [[Proxy System]], [[Project Settings]], [[CI CD Pipeline]], [[API Endpoints Reference]], [[Payment Processing]]
- Pages updated: [[overview]]
- Key insight: Full VPN service backend with 3 Django apps, 5 auth methods, 3 payment gateways, external VPN panel integration via Remnawave API.
