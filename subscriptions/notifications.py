"""Telegram notification system for EIFAVPN."""
import logging
import secrets
import string
import requests
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.db.models import F

from accounts.models import User, Subscription, PromoCode, PromoCodeUsage

logger = logging.getLogger(__name__)

TOKEN = None
MINIAPP_URL = 'https://t.me/eifavpn_bot/eifavpn'
STICKER_WELCOME = 'CAACAgIAAxkBAAEDO5pp3liz7YA-_G-tjyFQqfZurhmWjAACs5cAAvpe0UpIU2YPTiZsujsE'

# Premium emoji IDs
E = {
    'heart': '5391239629376625377',   # ❤️
    'lock': '5391195004666419042',    # 🔐
    'crown': '5393467918539330512',   # 👑
    'cd': '5391258089146061893',      # 💿
    'server': '5393079047905384579',  # 🗄
    'gift': '5391268461492081011',    # 🎁
    'handshake': '5391367877100082462',  # 🤝
    'sword': '5393484935199757766',   # ⚔
}


def _e(emoji_id, fallback='✨'):
    # Premium emoji require bot with Telegram Premium — use fallback for now
    return fallback


def _token():
    global TOKEN
    if not TOKEN:
        TOKEN = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    return TOKEN


def _send_message(chat_id, text, reply_markup=None):
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        resp = requests.post(
            f'https://api.telegram.org/bot{_token()}/sendMessage',
            json=payload, timeout=10,
        )
        if not resp.ok:
            logger.error(f'TG send failed to {chat_id}: {resp.status_code} {resp.text[:200]}')
        return resp.ok
    except Exception as e:
        logger.error(f'TG send failed to {chat_id}: {e}')
        return False


def _send_sticker(chat_id, sticker_id):
    try:
        requests.post(
            f'https://api.telegram.org/bot{_token()}/sendSticker',
            json={'chat_id': chat_id, 'sticker': sticker_id},
            timeout=10,
        )
    except Exception:
        pass


def _open_button():
    return {
        'inline_keyboard': [[{
            'text': 'Открыть EIFAVPN',
            'url': MINIAPP_URL,
            'style': 'success',
            'icon_custom_emoji_id': E['heart'],
        }]]
    }


def _generate_code(prefix='BACK'):
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(secrets.choice(chars) for _ in range(5))
    return f'{prefix}{suffix}'


# ──────────────────────────────────────────────
# 1. Welcome message on /start
# ──────────────────────────────────────────────

def send_welcome(chat_id, first_name=''):
    name = first_name or 'друг'
    _send_sticker(chat_id, STICKER_WELCOME)
    text = (
        f'{_e(E["crown"], "👑")} <b>Добро пожаловать в EIFA VPN!</b>\n\n'
        f'Привет, {name}!\n\n'
        f'{_e(E["lock"], "🔐")} Безопасный и быстрый VPN\n'
        f'{_e(E["server"], "🗄")} Серверы по всему миру\n'
        f'{_e(E["sword"], "⚔")} Безлимитный трафик\n'
        f'{_e(E["cd"], "💿")} Оплата Telegram Stars\n\n'
        f'Нажми кнопку ниже, чтобы открыть приложение:'
    )
    _send_message(chat_id, text, reply_markup={
        'inline_keyboard': [[{
            'text': 'Открыть EIFAVPN',
            'url': MINIAPP_URL,
            'style': 'success',
            'icon_custom_emoji_id': E['heart'],
        }]]
    })


# ──────────────────────────────────────────────
# 2. Purchase success notification
# ──────────────────────────────────────────────

def notify_purchase_success(user, subscription):
    if not user.telegram_id:
        return
    plan_name = subscription.plan.capitalize()
    period = subscription.period_months
    period_str = f'{period} мес' if period else ''
    text = (
        f'{_e(E["crown"], "👑")} <b>Подписка оформлена!</b>\n\n'
        f'{_e(E["heart"], "❤️")} Спасибо за покупку!\n\n'
        f'{_e(E["lock"], "🔐")} Тариф: <b>{plan_name}</b>\n'
        f'{_e(E["cd"], "💿")} Период: {period_str}\n'
        f'{_e(E["server"], "🗄")} Серверы уже доступны\n\n'
        f'Подключайтесь через приложение:'
    )
    _send_message(user.telegram_id, text, reply_markup=_open_button())


# ──────────────────────────────────────────────
# 3. Subscription expiring (3 days / 1 day)
# ──────────────────────────────────────────────

def notify_expiring(user, days_left):
    if not user.telegram_id:
        return
    if days_left == 3:
        text = (
            f'{_e(E["sword"], "⚔")} <b>Подписка заканчивается через 3 дня</b>\n\n'
            f'{_e(E["lock"], "🔐")} Продлите подписку, чтобы не потерять доступ к VPN.\n\n'
            f'{_e(E["handshake"], "🤝")} Все ваши настройки и устройства сохранятся.'
        )
    elif days_left == 1:
        text = (
            f'{_e(E["sword"], "⚔")} <b>Подписка заканчивается завтра!</b>\n\n'
            f'{_e(E["heart"], "❤️")} Остался <b>1 день</b>. '
            f'Продлите сейчас, чтобы VPN не отключился.\n\n'
            f'{_e(E["crown"], "👑")} Не теряйте свою защиту!'
        )
    else:
        return
    _send_message(user.telegram_id, text, reply_markup=_open_button())


# ──────────────────────────────────────────────
# 4. Subscription expired
# ──────────────────────────────────────────────

def notify_expired(user):
    if not user.telegram_id:
        return
    text = (
        f'{_e(E["sword"], "⚔")} <b>Подписка истекла</b>\n\n'
        f'{_e(E["lock"], "🔐")} Ваш VPN отключён. '
        f'Продлите подписку, чтобы восстановить доступ.\n\n'
        f'{_e(E["handshake"], "🤝")} Все настройки сохранены — просто продлите!'
    )
    _send_message(user.telegram_id, text, reply_markup=_open_button())


# ──────────────────────────────────────────────
# 5. Personal promo after 1 day expired (once)
# ──────────────────────────────────────────────

def notify_expired_with_promo(user):
    """Send personal 10% promo code 1 day after expiry. Only once per user."""
    if not user.telegram_id:
        return

    # Check if we already sent a winback promo to this user
    if PromoCode.objects.filter(
        code__startswith='BACK',
        created_by=None,
        subscriptions__user=user,
    ).exists():
        return  # Already sent once

    # Also check by tag in description
    existing = PromoCode.objects.filter(
        description__contains=f'winback_user_{user.id}'
    ).first()
    if existing:
        return

    # Generate personal promo
    code = _generate_code('BACK')
    while PromoCode.objects.filter(code=code).exists():
        code = _generate_code('BACK')

    promo = PromoCode.objects.create(
        code=code,
        promo_type='percent',
        value=10,
        max_uses=1,
        per_user_limit=1,
        description=f'winback_user_{user.id}',
        is_active=True,
    )

    text = (
        f'{_e(E["gift"], "🎁")} <b>Персональное предложение!</b>\n\n'
        f'{_e(E["heart"], "❤️")} Мы заметили, что ваша подписка закончилась.\n\n'
        f'Специально для вас — промокод на <b>скидку 10%</b>:\n\n'
        f'<code>{code}</code>\n\n'
        f'{_e(E["crown"], "👑")} Действует на все тарифы и сроки.\n'
        f'{_e(E["handshake"], "🤝")} Используйте при покупке!'
    )
    _send_message(user.telegram_id, text, reply_markup=_open_button())


# ──────────────────────────────────────────────
# Cron runner: check all subscriptions
# ──────────────────────────────────────────────

def run_subscription_notifications():
    """Called by cron/management command daily."""
    now = timezone.now()
    today = now.date()

    # Get all paid subscriptions
    subs = Subscription.objects.filter(status='paid').select_related('user')

    sent = {'3day': 0, '1day': 0, 'expired': 0, 'promo': 0}

    for sub in subs:
        user = sub.user
        if not user.telegram_id:
            continue

        expires = sub.expires_at.date()
        days_left = (expires - today).days

        if days_left == 3:
            notify_expiring(user, 3)
            sent['3day'] += 1
        elif days_left == 1:
            notify_expiring(user, 1)
            sent['1day'] += 1
        elif days_left == 0:
            notify_expired(user)
            sent['expired'] += 1
        elif days_left == -1:
            # 1 day after expiry — send personal promo (once)
            notify_expired_with_promo(user)
            sent['promo'] += 1

    return sent
