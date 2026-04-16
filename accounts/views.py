from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.conf import settings
from django.db.models import Q
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, UpdateProfileSerializer
from .models import User, Referral, EmailVerification
from django.core.mail import send_mail


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


class SendCodeView(APIView):
    """POST /api/auth/send-code/ — send 6-digit verification code to email."""
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        if not email or '@' not in email:
            return Response({'error': 'Укажите корректный email'}, status=status.HTTP_400_BAD_REQUEST)

        # Rate limit: max 1 code per minute per email
        from django.utils import timezone
        from datetime import timedelta
        recent = EmailVerification.objects.filter(
            email=email, created_at__gte=timezone.now() - timedelta(minutes=1)
        ).exists()
        if recent:
            return Response({'error': 'Код уже отправлен. Подождите минуту.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        code = EmailVerification.generate_code()
        EmailVerification.objects.create(email=email, code=code)

        email_sent = False
        try:
            send_mail(
                subject='EIFAVPN — Код подтверждения',
                message=f'Ваш код подтверждения: {code}\n\nКод действителен 10 минут.\n\nЕсли вы не запрашивали код, проигнорируйте это письмо.',
                html_message=f'''
                <div style="font-family: sans-serif; max-width: 400px; margin: 0 auto; padding: 32px; background: #0a1a1f; color: #e0f0f0; border-radius: 16px;">
                    <img src="https://eifavpn.ru/logo.png" alt="EIFAVPN" style="height: 40px; margin-bottom: 20px;" />
                    <h2 style="color: #5cebd6; margin: 0 0 8px;">Код подтверждения</h2>
                    <p style="color: #8aa; margin: 0 0 20px;">Используйте этот код для входа или регистрации:</p>
                    <div style="background: #0d2229; padding: 16px; border-radius: 12px; text-align: center; border: 1px solid #1a3a40;">
                        <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #5cebd6;">{code}</span>
                    </div>
                    <p style="color: #667; font-size: 12px; margin-top: 20px;">Код действителен 10 минут. Если вы не запрашивали код, проигнорируйте это письмо.</p>
                </div>
                ''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            email_sent = True
        except Exception as e:
            import logging
            logging.warning(f'Email send failed for {email}: {e}')
            email_sent = False

        resp = {'detail': 'Код отправлен на email', 'email': email}
        if not email_sent:
            import logging
            logging.error(f'CRITICAL: Email delivery failed for {email}. Code NOT returned to client.')
            resp['detail'] = 'Ошибка отправки email. Попробуйте позже или войдите через Google/Telegram.'
            return Response(resp, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(resp)


class VerifyCodeView(APIView):
    """POST /api/auth/verify-code/ — verify code + register or login."""
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        code = (request.data.get('code') or '').strip()
        password = request.data.get('password', '')
        name = request.data.get('name', '')
        referral_code = request.data.get('referral_code', '')

        if not email or not code:
            return Response({'error': 'Укажите email и код'}, status=status.HTTP_400_BAD_REQUEST)

        # Find valid code
        verification = EmailVerification.objects.filter(
            email=email, code=code, used=False
        ).order_by('-created_at').first()

        if not verification:
            return Response({'error': 'Неверный код'}, status=status.HTTP_400_BAD_REQUEST)

        if verification.is_expired():
            return Response({'error': 'Код истёк. Запросите новый.'}, status=status.HTTP_400_BAD_REQUEST)

        verification.used = True
        verification.save()

        # Find or create user
        user = User.objects.filter(email=email).first()
        is_new = user is None

        if user:
            # Existing user — login
            user.email_verified = True
            user.save()
        else:
            # New user — register
            referred_by = None
            if referral_code:
                referred_by = User.objects.filter(referral_code=referral_code).first()

            user = User.objects.create_user(
                email=email,
                password=password if password else None,
                first_name=name,
                referred_by=referred_by,
                email_verified=True,
            )

        tokens = get_tokens_for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
            'is_new': is_new,
        })


class RegisterView(APIView):
    """Legacy register (still works for quick registration without email verification)."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data['email'].lower(),
            password=serializer.validated_data['password'],
        )

        if not user:
            return Response(
                {'error': 'Неверный email или пароль'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = get_tokens_for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
        })


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UpdateProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass
        return Response({'detail': 'Logged out'})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get('old_password', '')
        new_password = request.data.get('new_password', '')

        if not old_password or not new_password:
            return Response(
                {'error': 'Укажите старый и новый пароль'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(new_password) < 6:
            return Response(
                {'error': 'Новый пароль должен быть не менее 6 символов'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user

        if not user.has_usable_password():
            # User registered via OAuth, allow setting password without old one
            user.set_password(new_password)
            user.save()
            return Response({'detail': 'Пароль установлен'})

        if not user.check_password(old_password):
            return Response(
                {'error': 'Неверный текущий пароль'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()
        return Response({'detail': 'Пароль изменён'})


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        password = request.data.get('password', '')
        user = request.user

        # Require password confirmation (skip for OAuth-only users)
        if user.has_usable_password() and not user.check_password(password):
            return Response({'error': 'Неверный пароль'}, status=status.HTTP_400_BAD_REQUEST)

        # Disable Remnawave subscription if exists
        if user.remnawave_uuid:
            try:
                import requests as req
                req.patch(
                    f'{settings.REMNAWAVE_API_URL}/users',
                    json={'uuid': str(user.remnawave_uuid), 'status': 'DISABLED'},
                    headers={
                        'Authorization': f'Bearer {settings.REMNAWAVE_BEARER_TOKEN}',
                        'Content-Type': 'application/json',
                    },
                    timeout=10,
                )
            except Exception:
                pass

        user.delete()
        return Response({'detail': 'Аккаунт удалён'})


class TelegramWebAppAuthView(APIView):
    """POST /api/auth/telegram-webapp/ — auth via Telegram Mini App initData OR Login Widget."""
    permission_classes = [AllowAny]

    def post(self, request):
        init_data_raw = request.data.get('initData', '')
        widget_data = request.data.get('widgetData')

        if widget_data:
            return self._auth_widget(widget_data)
        if init_data_raw:
            return self._auth_init_data(init_data_raw)

        return Response({'error': 'initData or widgetData is required'}, status=status.HTTP_400_BAD_REQUEST)

    def _auth_init_data(self, init_data_raw):
        """Authenticate via Telegram Mini App initData (HMAC validation)."""
        try:
            from init_data_py import InitData

            init_data = InitData.parse(init_data_raw)
            if not init_data.validate(bot_token=settings.TELEGRAM_BOT_TOKEN, lifetime=86400):
                return Response({'error': 'Invalid or expired initData'}, status=status.HTTP_401_UNAUTHORIZED)

            tg_user = init_data.user
            if not tg_user or not tg_user.id:
                return Response({'error': 'No user data in initData'}, status=status.HTTP_400_BAD_REQUEST)

            telegram_id = tg_user.id
            first_name = getattr(tg_user, 'first_name', '') or ''

        except Exception as e:
            return Response({'error': f'initData validation failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        return self._find_or_create_user(telegram_id, first_name)

    def _auth_widget(self, widget_data):
        """Authenticate via Telegram Login Widget (hash-based verification)."""
        import hashlib
        import hmac as hmac_mod
        import time

        if not isinstance(widget_data, dict) or 'hash' not in widget_data or 'id' not in widget_data:
            return Response({'error': 'Invalid widget data'}, status=status.HTTP_400_BAD_REQUEST)

        received_hash = widget_data['hash']
        if not isinstance(received_hash, str):
            return Response({'error': 'Invalid widget data'}, status=status.HTTP_400_BAD_REQUEST)

        # Verify auth_date is not too old (24 hours, one-directional — no future dates)
        auth_date = int(widget_data.get('auth_date', 0))
        if time.time() - auth_date > 86400 or auth_date < 0:
            return Response({'error': 'Widget auth expired'}, status=status.HTTP_401_UNAUTHORIZED)

        # Verify hash: https://core.telegram.org/widgets/login#checking-authorization
        check_fields = {k: str(v) for k, v in widget_data.items() if k != 'hash' and v is not None}
        data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(check_fields.items()))

        secret_key = hashlib.sha256(settings.TELEGRAM_BOT_TOKEN.encode()).digest()
        computed_hash = hmac_mod.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if not hmac_mod.compare_digest(computed_hash, received_hash):
            return Response({'error': 'Invalid widget hash'}, status=status.HTTP_401_UNAUTHORIZED)

        telegram_id = int(widget_data['id'])
        first_name = str(widget_data.get('first_name', ''))

        return self._find_or_create_user(telegram_id, first_name)

    def _find_or_create_user(self, telegram_id, first_name=''):
        """Find or create user by telegram_id, return JWT tokens."""
        user = User.objects.filter(telegram_id=telegram_id).first()

        if not user:
            email = f'tg_{telegram_id}@eifavpn.ru'
            user = User.objects.create_user(
                email=email,
                first_name=first_name,
                telegram_id=telegram_id,
                email_verified=True,
            )
        else:
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                user.save(update_fields=['first_name'])

        tokens = get_tokens_for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
        })


def _mask_email(email):
    """Mask email: show first 2 chars + *** + @domain."""
    if not email or '@' not in email:
        return '***'
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        masked = local[0] + '***'
    else:
        masked = local[:2] + '***'
    return f'{masked}@{domain}'


class PrepareShareView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.telegram_id:
            return Response({'error': 'Telegram not linked'}, status=status.HTTP_400_BAD_REQUEST)

        import requests as req
        bot_token = settings.TELEGRAM_BOT_TOKEN

        result = req.post(f'https://api.telegram.org/bot{bot_token}/savePreparedInlineMessage', json={
            'user_id': user.telegram_id,
            'result': {
                'type': 'article',
                'id': f'ref_{user.referral_code}',
                'title': 'EIFAVPN — Безопасный VPN',
                'input_message_content': {
                    'message_text': f'\U0001f512 EIFAVPN \u2014 быстрый и безопасный VPN\n\nПопробуй бесплатно 3 дня MAX!\n\n\U0001f449 https://eifavpn.ru/register?ref={user.referral_code}',
                    'parse_mode': 'HTML',
                },
                'description': 'Получи 3 дня бесплатного VPN',
            },
            'allow_user_chats': True,
            'allow_group_chats': True,
            'allow_channel_chats': True,
        }, timeout=10)

        data = result.json()
        if data.get('ok'):
            return Response({'id': data['result']['id']})
        return Response({'error': data.get('description', 'Failed')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LinkEmailView(APIView):
    """POST /api/auth/link-email/ — send verification code to new email."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        email = (request.data.get('email') or '').strip().lower()

        # Google users can't change email
        if user.google_id:
            return Response({'error': 'Google-аккаунт уже привязан, email изменить нельзя'}, status=400)

        # Don't allow if email is already a real email (not tg_*)
        if not user.email.startswith('tg_') and '@eifavpn.ru' not in user.email:
            return Response({'error': 'Email уже привязан'}, status=400)

        if not email or '@' not in email:
            return Response({'error': 'Укажите корректный email'}, status=400)

        # Check email not taken
        if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            return Response({'error': 'Этот email уже используется'}, status=400)

        # Rate limit
        from django.utils import timezone
        from datetime import timedelta
        recent = EmailVerification.objects.filter(
            email=email, created_at__gte=timezone.now() - timedelta(minutes=1)
        ).exists()
        if recent:
            return Response({'error': 'Код уже отправлен. Подождите минуту.'}, status=429)

        code = EmailVerification.generate_code()
        EmailVerification.objects.create(email=email, code=code)

        # Send email
        try:
            send_mail(
                subject='EIFAVPN — Привязка email',
                message=f'Код привязки email: {code}',
                html_message=f'<div style="font-family:sans-serif;max-width:400px;margin:0 auto;padding:32px;background:#0a1a1f;color:#e0f0f0;border-radius:16px;"><h2 style="color:#5cebd6;">Привязка email</h2><p>Код подтверждения:</p><div style="background:#0d2229;padding:16px;border-radius:12px;text-align:center;"><span style="font-size:32px;font-weight:bold;letter-spacing:8px;color:#5cebd6;">{code}</span></div><p style="color:#667;font-size:12px;">Код действителен 10 минут.</p></div>',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception:
            return Response({'error': 'Ошибка отправки email'}, status=503)

        return Response({'detail': 'Код отправлен', 'email': email})


class LinkEmailVerifyView(APIView):
    """POST /api/auth/link-email/verify/ — verify code and link email."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        email = (request.data.get('email') or '').strip().lower()
        code = (request.data.get('code') or '').strip()

        if not email or not code:
            return Response({'error': 'Укажите email и код'}, status=400)

        verification = EmailVerification.objects.filter(
            email=email, code=code, used=False
        ).order_by('-created_at').first()

        if not verification:
            return Response({'error': 'Неверный код'}, status=400)
        if verification.is_expired():
            return Response({'error': 'Код истёк'}, status=400)

        # Check email not taken
        if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            return Response({'error': 'Этот email уже используется'}, status=400)

        verification.used = True
        verification.save()

        user.email = email
        user.email_verified = True
        user.save(update_fields=['email', 'email_verified'])

        return Response(UserSerializer(user).data)


class LinkTelegramView(APIView):
    """POST /api/auth/link-telegram/ — link Telegram to existing account."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        init_data_raw = request.data.get('initData', '')

        if user.telegram_id:
            return Response({'error': 'Telegram уже привязан'}, status=400)

        if not init_data_raw:
            return Response({'error': 'initData required'}, status=400)

        try:
            from init_data_py import InitData
            init_data = InitData.parse(init_data_raw)
            if not init_data.validate(bot_token=settings.TELEGRAM_BOT_TOKEN, lifetime=86400):
                return Response({'error': 'Invalid initData'}, status=401)

            tg_user = init_data.user
            telegram_id = tg_user.id if tg_user else None
        except Exception:
            return Response({'error': 'Ошибка валидации Telegram'}, status=400)

        if not telegram_id:
            return Response({'error': 'Не удалось получить Telegram ID'}, status=400)

        # Check telegram_id not taken
        if User.objects.filter(telegram_id=telegram_id).exclude(pk=user.pk).exists():
            return Response({'error': 'Этот Telegram уже привязан к другому аккаунту'}, status=400)

        user.telegram_id = telegram_id
        user.save(update_fields=['telegram_id'])

        return Response(UserSerializer(user).data)


class ReferralMyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.utils import timezone
        from django.db.models import Sum, Count

        user = request.user
        all_referrals = Referral.objects.filter(referrer=user)
        total_referrals = all_referrals.count()
        paid_referrals = all_referrals.filter(bonus_applied=True).count()
        app_url = getattr(settings, 'APP_URL', 'https://eifavpn.ru')

        # This month
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        referrals_this_month = all_referrals.filter(created_at__gte=month_start).count()

        # Conversion rate
        conversion_rate = round(paid_referrals / max(total_referrals, 1) * 100, 1)

        # Total savings by referees (10% of each referred user's first paid subscription)
        from accounts.models import Subscription
        referred_user_ids = list(all_referrals.values_list('referred_id', flat=True))
        total_savings = 0
        if referred_user_ids:
            total_paid = Subscription.objects.filter(
                user_id__in=referred_user_ids, status='paid'
            ).exclude(payment_method='trial').aggregate(s=Sum('price_paid'))['s'] or 0
            total_savings = round(float(total_paid) * 0.10)

        return Response({
            'code': user.referral_code,
            'link': f'{app_url}/register?ref={user.referral_code}',
            'total_referrals': total_referrals,
            'paid_referrals': paid_referrals,
            'referrals_this_month': referrals_this_month,
            'conversion_rate': conversion_rate,
            'bonus_days_earned': user.referral_bonus_days,
            'total_savings_rub': total_savings,
        })


class ReferralStatsView(APIView):
    """GET /api/referral/stats/ — per-month referral breakdown."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models.functions import TruncMonth
        from django.db.models import Count

        user = request.user
        monthly = (
            Referral.objects.filter(referrer=user)
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(
                total=Count('id'),
                paid=Count('id', filter=Q(bonus_applied=True)),
            )
            .order_by('month')
        )

        result = []
        for row in monthly:
            result.append({
                'month': row['month'].strftime('%Y-%m'),
                'total': row['total'],
                'paid': row['paid'],
            })

        return Response(result)


class ReferralListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        referrals = Referral.objects.filter(
            referrer=request.user
        ).select_related('referred', 'subscription').order_by('-created_at')

        result = []
        for ref in referrals:
            result.append({
                'email': _mask_email(ref.referred.email),
                'date': ref.created_at.strftime('%Y-%m-%d'),
                'subscribed': ref.subscription is not None and ref.subscription.status == 'paid',
            })

        return Response(result)
