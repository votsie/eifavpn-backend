from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.conf import settings
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, UpdateProfileSerializer
from .models import User, Referral


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


class RegisterView(APIView):
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
