---
title: Wiki Index
type: meta
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [meta, index]
---

# EIFAVPN Backend Wiki

> [!key-insight] Project Identity
> Django 6.x REST API для VPN-сервиса с Telegram Mini App фронтендом. 3 Django-приложения, 5 методов аутентификации, 3 платёжных шлюза, внешняя VPN-панель Remnawave.

## Overview

- [[overview]] — Обзор проекта, стек, архитектура

## Sources (Django Apps)

- [[Accounts App]] — Пользователи, аутентификация, реферальная система
- [[API App]] — Google/Telegram OAuth, прокси к Remnawave
- [[Subscriptions App]] — Тарифы, покупки, платежи, webhooks, уведомления

## Entities (Models)

- [[User Model]] — Кастомный User (email-based, multi-auth, referrals)
- [[Subscription Model]] — Подписки (plan, status, payment, expires_at)
- [[Referral Model]] — Реферальные связи и бонусы
- [[EmailVerification Model]] — 6-значные коды верификации email
- [[PromoCode Model]] — Промокоды (percent/days/gift)

## Entities (External Services)

- [[Remnawave]] — VPN-панель (wavepanel.eifastore.ru)
- [[CryptoPay]] — Криптовалютный платёжный шлюз
- [[Wata H2H]] — Российские карты и СБП
- [[Telegram Stars]] — Внутренняя валюта Telegram
- [[Telegram Bot Integration]] — Уведомления, шаринг, welcome

## Concepts (Business Logic)

- [[Authentication Flows]] — Email code, Google, Telegram (3 варианта)
- [[Subscription Lifecycle]] — Trial → Purchase → Payment → Activation → Expiry → Winback
- [[Referral System]] — 10% скидка + 7 дней бонус
- [[Promo Code System]] — percent/days/gift промокоды
- [[Payment Processing]] — Stars, CryptoPay, Wata H2H
- [[Remnawave Integration]] — API-клиент и CRUD подписок
- [[Proxy System]] — Secure gateway к Remnawave с whitelist + ownership
- [[JWT Authentication]] — simplejwt конфигурация
- [[Security Review]] — Аудит безопасности 2026-04-16 (P0-P2 fixes)

## Domains (Infrastructure)

- [[Project Settings]] — Django settings (base/dev/prod)
- [[CI CD Pipeline]] — GitHub Actions деплой
- [[API Endpoints Reference]] — Полный список 30+ эндпоинтов

## Cross-Project

- [[EIFAVPN Frontend]] — React 19 SPA (eifavpn-frontend/wiki/)

## Meta

- [[hot]] — Hot cache для быстрого старта сессии
- [[log]] — Лог всех ingests
- [[Lint Report 2026-04-16]] — Результаты wiki lint
- [[Dashboard]] — Dataview queries dashboard
