import secrets
import string
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


def generate_referral_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(8))


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        extra_fields.setdefault('username', email.split('@')[0])
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField(unique=True)
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    google_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    avatar_url = models.URLField(blank=True, default='')

    # Remnawave
    remnawave_uuid = models.UUIDField(null=True, blank=True)
    remnawave_short_uuid = models.CharField(max_length=64, blank=True, default='')
    subscription_url = models.URLField(blank=True, default='')

    # Referral
    referral_code = models.CharField(max_length=16, unique=True, default=generate_referral_code)
    referred_by = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals'
    )
    referral_bonus_days = models.IntegerField(default=0)

    # Trial funnel
    used_trial = models.BooleanField(default=False)
    used_trial_upgrade = models.BooleanField(default=False)

    # Email verification
    email_verified = models.BooleanField(default=False)

    # Auto-renewal
    auto_renew = models.BooleanField(default=False)
    preferred_payment_method = models.CharField(max_length=32, blank=True, default='')
    preferred_crypto_asset = models.CharField(max_length=16, blank=True, default='USDT')

    # Notification preferences
    notification_prefs = models.JSONField(default=dict, blank=True)

    # Pending promo code — applied from URL ?promo= when user not yet authenticated,
    # consumed on first purchase. See PromoInput.jsx + ApplyPendingPromoView.
    pending_promo_code = models.CharField(max_length=32, blank=True, default='')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class Subscription(models.Model):
    PLAN_CHOICES = [('standard', 'Standard'), ('pro', 'Pro'), ('max', 'Max')]
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('paid', 'Paid'),
        ('cancelled', 'Cancelled'), ('expired', 'Expired'),
        ('error', 'Error'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    period_months = models.IntegerField()
    price_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=32)
    payment_id = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    remnawave_uuid = models.UUIDField(null=True, blank=True)
    upgrade_from = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='upgrades')
    # Promo code applied to this subscription (nullable — trials/gifts don't have one).
    # String FK to avoid ImportError when PromoCode model is absent.
    promo_code = models.ForeignKey(
        'PromoCode', null=True, blank=True, on_delete=models.SET_NULL, related_name='subscriptions'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} — {self.plan} ({self.status})'


class Referral(models.Model):
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referral_rewards')
    referred = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referred_by_record')
    subscription = models.ForeignKey(Subscription, null=True, blank=True, on_delete=models.SET_NULL)
    bonus_applied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.referrer.email} → {self.referred.email}'


class EmailVerification(models.Model):
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    @staticmethod
    def generate_code():
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

    def is_expired(self):
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() > self.created_at + timedelta(minutes=10)


class PromoCode(models.Model):
    """Promo codes for subscriptions. 3 types: percent discount, bonus days, free gift."""
    PROMO_TYPES = [
        ('percent', 'Percent discount'),
        ('days', 'Bonus days'),
        ('gift', 'Free gift (activate without purchase)'),
    ]

    code = models.CharField(max_length=32, unique=True, db_index=True)
    promo_type = models.CharField(max_length=16, choices=PROMO_TYPES, default='percent')
    value = models.IntegerField(default=0, help_text='% discount, bonus days, or gift days depending on type')
    description = models.CharField(max_length=255, blank=True, default='')

    # Restrictions
    plan = models.CharField(max_length=20, blank=True, default='', help_text='Restrict to plan (standard/pro/max), empty = any')
    allowed_periods = models.JSONField(default=list, blank=True, help_text='List of allowed periods (1,3,6,12), empty = any')
    max_uses = models.IntegerField(default=0, help_text='Global usage limit, 0 = unlimited')
    per_user_limit = models.IntegerField(default=1, help_text='Max uses per single user')

    # State
    is_active = models.BooleanField(default=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    times_used = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='created_promos'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.code} ({self.promo_type}={self.value})'


class PromoCodeUsage(models.Model):
    """Audit log of promo code applications."""
    promo = models.ForeignKey(PromoCode, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promo_usages')
    subscription = models.ForeignKey(
        Subscription, null=True, blank=True, on_delete=models.SET_NULL, related_name='promo_usages'
    )
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonus_days = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        # Prevent the same user from using the same promo beyond per_user_limit via DB constraint assist
        indexes = [models.Index(fields=['promo', 'user'])]

    def __str__(self):
        return f'{self.user.email} used {self.promo.code}'


class SupportTicket(models.Model):
    PRIORITY_CHOICES = [('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')]
    STATUS_CHOICES = [
        ('open', 'Open'), ('in_progress', 'In Progress'),
        ('waiting', 'Waiting for User'), ('resolved', 'Resolved'), ('closed', 'Closed'),
    ]
    CATEGORY_CHOICES = [
        ('connection', 'Проблемы с подключением'),
        ('payment', 'Вопросы оплаты'),
        ('account', 'Проблемы с аккаунтом'),
        ('speed', 'Скорость/качество'),
        ('feature', 'Предложение'),
        ('other', 'Другое'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    subject = models.CharField(max_length=255)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default='other')
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    assigned_to = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_tickets'
    )
    telegram_chat_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'#{self.id} {self.subject} ({self.status})'


class TicketMessage(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    is_staff = models.BooleanField(default=False)
    text = models.TextField()
    telegram_message_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        who = 'Staff' if self.is_staff else 'User'
        return f'{who}: {self.text[:50]}'
