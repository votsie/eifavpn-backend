---
title: CI/CD Pipeline
type: domain
domain: infrastructure
status: developing
created: 2026-04-16
updated: 2026-04-16
tags: [domain, infrastructure, ci-cd]
---

# CI/CD Pipeline

Автоматический деплой через GitHub Actions при push в целевую ветку.

## Сервер

- **IP**: 5.101.81.90
- **SSH User**: root
- **Auth**: пароль через GitHub Secret `SSH_PASSWORD`
- Dev и Prod на одном сервере в разных директориях

## Deploy Dev

**Файл**: `.github/workflows/deploy-dev.yml`
**Триггер**: push в `dev` ветку

```
1. Checkout dev branch
2. SSH → cd /opt/eifavpn/dev/backend
3. git pull origin dev
4. source venv/bin/activate
5. pip install -r requirements.txt -q
6. DJANGO_SETTINGS_MODULE=eifavpn.settings.dev python manage.py migrate --noinput
7. systemctl restart eifavpn-dev
```

## Deploy Prod

**Файл**: `.github/workflows/deploy-prod.yml`
**Триггер**: push в `main` ветку

```
1. Checkout main branch
2. SSH → cd /opt/eifavpn/prod/backend
3. git pull origin main
4. source venv/bin/activate
5. pip install -r requirements.txt -q
6. DJANGO_SETTINGS_MODULE=eifavpn.settings.prod python manage.py migrate --noinput
7. python manage.py collectstatic --noinput
8. systemctl restart eifavpn-prod
```

**Отличие от dev**: collectstatic для статических файлов.

## Systemd-сервисы

| Service | Path | Branch |
|---------|------|--------|
| `eifavpn-dev` | `/opt/eifavpn/dev/backend` | dev |
| `eifavpn-prod` | `/opt/eifavpn/prod/backend` | main |

## Секреты GitHub

- `SSH_PASSWORD` — пароль root для SSH

> [!gap] Рекомендация
> Использовать SSH-ключи вместо пароля. Рассмотреть разделение dev/prod серверов.

## См. также

- [[Project Settings]] — конфигурация окружений
