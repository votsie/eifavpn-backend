---
title: Hot Cache
type: meta
status: developing
created: 2026-04-16
updated: 2026-04-16
purpose: Quick-load context for future sessions
tags: [meta, hot-cache]
---

# Hot Cache

## Project Identity
- **Name**: eifavpn-backend
- **Type**: Django 6.x REST API for VPN service
- **Frontend**: Telegram Mini App
- **VPN Panel**: Remnawave (wavepanel.eifastore.ru)
- **Domain**: eifavpn.ru (prod), dev.eifavpn.ru (dev)

## Apps
- `accounts` — User model (email-based, multi-auth), referrals, email verification
- `api` — Google/Telegram OAuth callbacks, Remnawave proxy
- `subscriptions` — Plans (standard/pro/max), payments (Stars/Crypto/Wata), webhooks, notifications

## Key Models
- `User` (accounts) — email as USERNAME_FIELD, telegram_id, google_id, remnawave_uuid, referral_code
- `Subscription` (accounts) — plan, period_months, status (pending/paid/cancelled/expired), payment_method
- `Referral` (accounts) — referrer→referred tracking, bonus_applied flag
- `EmailVerification` (accounts) — 6-digit codes, 10min expiry
- `PromoCode` (accounts) — percent/days/gift types, per-user limits

## External Services
- **Remnawave**: POST/PATCH /users for VPN subscription CRUD
- **CryptoPay**: createInvoice → webhook with HMAC-SHA256
- **Wata H2H**: POST /api/h2h/links/ → webhook
- **Telegram Stars**: createInvoiceLink → pre_checkout_query → successful_payment
- **Telegram Bot API**: notifications, welcome messages, inline sharing

## Auth Methods
1. Email + 6-digit code (passwordless primary)
2. Google OAuth 2.0 (authorization code flow)
3. Telegram OAuth 2.0 (code + JWT flows)
4. Telegram Mini App initData (HMAC validation)

## Pricing (RUB/month)
- Standard: 69/59/55/45 (1/3/6/12 мес)
- Pro: 99/89/79/65
- Max: 149/129/119/99

## Frontend (Cross-Project)
- **Repo**: eifavpn-frontend (React 19 + Vite SPA)
- **Wiki**: `C:/Users/aafek/OneDrive/Документы/GitHub/eifavpn-frontend/wiki/`
- **Stack**: React 19, Router 7.14, Zustand 5, Tailwind 4, HeroUI 3
- **Layouts**: Landing (public), Cabinet (auth), Admin (staff), TG App (auto-login)
- **API modules**: client.js (auto-refresh), auth.js (15+), subscriptions.js, referrals.js, admin.js (30+)
- **Deploy**: GitHub Actions → SCP → same server 5.101.81.90

## Security Hardening (2026-04-16)
- JWT tokens → URL fragments (not query params)
- Wata webhook: server-to-server verification
- Stars webhook: secret token verification
- Google OAuth state: HMAC-signed
- Email codes: `secrets.randbelow` (crypto-safe)
- Production: HSTS, SSL redirect, secure cookies
- expires_at: recalculated from payment time
- Django admin: all models registered
- See: [[Security Review]]

## Latest Ingest
- 2026-04-16: Security audit + wiki lint — 13 code fixes, 33 wiki pages updated
- 2026-04-16: Full project scan — all modules documented
- 2026-04-16: Frontend cross-references added
