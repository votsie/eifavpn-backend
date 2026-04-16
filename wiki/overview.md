---
title: EIFAVPN Backend — Project Overview
updated: 2026-04-16
---

# EIFAVPN Backend

**EIFAVPN** — VPN-сервис с Telegram Mini App фронтендом и Django REST API бэкендом. Управление VPN-подключениями делегировано внешней панели [[Remnawave]].

## Стек технологий

| Компонент | Технология |
|-----------|-----------|
| Framework | Django 6.x + Django REST Framework 3.17 |
| Auth | [[JWT Authentication]] (simplejwt), Google OAuth 2.0, Telegram OAuth 2.0, Telegram Mini App initData |
| Database | PostgreSQL (psycopg2-binary) |
| HTTP client | httpx, requests |
| WSGI server | Gunicorn |
| VPN panel | [[Remnawave]] (wavepanel.eifastore.ru) |
| Payments | [[Telegram Stars]], [[CryptoPay]], [[Wata H2H]] |
| Notifications | Telegram Bot API |
| CI/CD | GitHub Actions → SSH deploy |
| Hosting | Single server 5.101.81.90 (dev + prod) |

## Django-приложения

| App | Назначение |
|-----|-----------|
| [[Accounts App]] | Пользователи, аутентификация, реферальная система, привязка аккаунтов |
| [[API App]] | Google/Telegram OAuth callbacks, прокси к [[Remnawave]] |
| [[Subscriptions App]] | Тарифы, покупки, платежи, webhooks, уведомления, промокоды |

## Архитектура

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│  Telegram Mini   │────▶│  Django API   │────▶│  PostgreSQL  │
│  App (Frontend)  │◀────│  (Backend)    │◀────│              │
└─────────────────┘     └──────┬───────┘     └──────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
             ┌───────────┐ ┌────────┐ ┌────────┐
             │ Remnawave │ │Payment │ │Telegram│
             │ VPN Panel │ │Gateways│ │Bot API │
             └───────────┘ └────────┘ └────────┘
```

## Окружения

| Env | Branch | Domain | Service |
|-----|--------|--------|---------|
| Dev | `dev` | dev.eifavpn.ru | eifavpn-dev |
| Prod | `main` | eifavpn.ru | eifavpn-prod |

Оба окружения на одном сервере, изолированы через отдельные директории и systemd-сервисы.

## Ключевые бизнес-процессы

1. **[[Authentication Flows]]** — Email code, Google OAuth, Telegram OAuth, Telegram Mini App
2. **[[Subscription Lifecycle]]** — Trial → Purchase → Payment → Activation → Expiry → Winback
3. **[[Referral System]]** — 10% скидка рефералу, +7 дней реферреру
4. **[[Promo Code System]]** — percent/days/gift типы промокодов
5. **[[Remnawave Integration]]** — CRUD подписок через внешний API
6. **[[Security Review]]** — Аудит безопасности (JWT transport, webhook verification, HMAC state)

## Фронтенд

Клиентская часть — React 19 SPA в отдельном репозитории. Полная документация: [[EIFAVPN Frontend]].

Ключевые связи:
- Фронтенд вызывает 50+ API-эндпоинтов бэкенда
- 4 метода аутентификации (email code, Google OAuth, Telegram Widget, TG Mini App)
- 3 платёжных шлюза (Stars, CryptoPay, Wata) — фронтенд open URL + polling, бэкенд webhooks
- Remnawave данные через proxy endpoint

## См. также

- [[EIFAVPN Frontend]] — React SPA документация
- [[Project Settings]] — Конфигурация Django
- [[CI CD Pipeline]] — GitHub Actions деплой
- [[API Endpoints Reference]] — Полный список эндпоинтов
