from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.conf import settings
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
        except Exception as e:
            return Response({'error': f'Ошибка отправки: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'detail': 'Код отправлен на email', 'email': email})


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
            'is_new': not User.objects.filter(email=email).exclude(pk=user.pk).exists(),
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


class ReferralMyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        total_referrals = Referral.objects.filter(referrer=user).count()
        app_url = getattr(settings, 'APP_URL', 'https://eifavpn.ru')

        return Response({
            'code': user.referral_code,
            'link': f'{app_url}/register?ref={user.referral_code}',
            'total_referrals': total_referrals,
            'bonus_days_earned': user.referral_bonus_days,
        })


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
