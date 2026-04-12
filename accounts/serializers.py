from rest_framework import serializers
from .models import User


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6, write_only=True)
    name = serializers.CharField(max_length=150, required=False, default='')
    referral_code = serializers.CharField(max_length=16, required=False, default='')

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Пользователь с таким email уже существует')
        return value.lower()

    def create(self, validated_data):
        referral_code = validated_data.pop('referral_code', '')
        name = validated_data.pop('name', '')

        referred_by = None
        if referral_code:
            referred_by = User.objects.filter(referral_code=referral_code).first()

        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=name,
            referred_by=referred_by,
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    has_subscription = serializers.SerializerMethodField()
    current_plan = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'avatar_url',
            'telegram_id', 'google_id',
            'remnawave_uuid', 'remnawave_short_uuid', 'subscription_url',
            'referral_code', 'referral_bonus_days',
            'used_trial', 'used_trial_upgrade',
            'has_subscription', 'current_plan',
            'date_joined',
        ]
        read_only_fields = [
            'id', 'referral_code', 'remnawave_uuid', 'remnawave_short_uuid',
            'subscription_url', 'date_joined',
        ]

    def get_has_subscription(self, obj):
        return obj.subscriptions.filter(status='paid').exists()

    def get_current_plan(self, obj):
        sub = obj.subscriptions.filter(status='paid').order_by('-expires_at').first()
        if sub:
            return {'plan': sub.plan, 'expires_at': sub.expires_at.isoformat(), 'period': sub.period_months}
        return None


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'avatar_url']
