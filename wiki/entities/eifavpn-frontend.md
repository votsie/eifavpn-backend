---
title: EIFAVPN Frontend
type: entity
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [entity, cross-project, frontend]
---

# EIFAVPN Frontend

> [!key-insight] Кросс-проектная ссылка
> Полная документация фронтенда в отдельной wiki: `eifavpn-frontend/wiki/`
> Путь: `C:/Users/aafek/OneDrive/Документы/GitHub/eifavpn-frontend/wiki/`

## Обзор

React 19 + Vite SPA. Работает как обычный сайт и как Telegram Mini App (@EIFA_VPNbot).

## Стек

React 19, React Router 7.14, Zustand 5, Tailwind CSS 4, HeroUI 3, Motion 12, Vite + Oxc.

## Структура

| Зона | Layout | Маршрут |
|------|--------|---------|
| Landing | LandingLayout | `/`, `/cabinet/login`, `/register`, `/terms` |
| Cabinet | CabinetLayout | `/cabinet/*` (6 страниц, auth required) |
| Admin | AdminLayout | `/admin/*` (14 маршрутов, staff only) |
| TG App | — | `/app` (auto-login через initData) |

## Как фронтенд взаимодействует с бэкендом

### API Client (`src/api/client.js`)
- Base: `/api` (VITE_API_URL)
- Bearer token из localStorage
- Auto-refresh при 401
- Error: `ApiError {status, data}`

### Используемые эндпоинты бэкенда
- **Auth**: send-code, verify-code, login, me, logout, link-email, link-telegram, link-google
- **Subscriptions**: plans, purchase, my, trial, devices, rates, validate-promo, activate-gift
- **Referrals**: my, list, prepare-share
- **Proxy**: nodes, hwid-user-devices
- **Admin**: 30+ endpoints
- **OAuth**: google, google/callback, telegram, telegram/callback

### Аутентификация
4 метода, все через JWT:
1. Email + 6-digit code → `verify-code/`
2. Google OAuth → redirect → `google/callback/` → tokens в URL
3. Telegram Widget → `telegram/callback/` с id_token
4. TG Mini App → `telegram-webapp/` с initData

### Оплата
Frontend открывает payment_url → user платит → webhook на бэкенд → polling `my/` со стороны фронта.

## Деплой

| Env | Branch | Deploy Path |
|-----|--------|-------------|
| Dev | `dev` | /opt/eifavpn/dev/frontend/ |
| Prod | `main` | /opt/eifavpn/prod/frontend/ |

GitHub Actions → `npm run build` → SCP на 5.101.81.90.

## См. также

- [[overview]] — Бэкенд overview
- [[Authentication Flows]] — Серверная сторона auth
- [[Subscription Lifecycle]] — Серверный lifecycle подписок
- [[API Endpoints Reference]] — Все серверные эндпоинты
