from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Subscription, Referral, EmailVerification


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'first_name', 'telegram_id', 'google_id', 'referral_code', 'used_trial', 'date_joined']
    list_filter = ['is_staff', 'is_active', 'used_trial', 'email_verified']
    search_fields = ['email', 'first_name', 'telegram_id', 'referral_code']
    ordering = ['-date_joined']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('VPN', {'fields': ('remnawave_uuid', 'remnawave_short_uuid', 'subscription_url')}),
        ('Referral', {'fields': ('referral_code', 'referred_by', 'referral_bonus_days')}),
        ('Trial', {'fields': ('used_trial', 'used_trial_upgrade')}),
        ('OAuth', {'fields': ('telegram_id', 'google_id', 'avatar_url', 'email_verified')}),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'period_months', 'price_paid', 'payment_method', 'status', 'created_at', 'expires_at']
    list_filter = ['status', 'plan', 'payment_method']
    search_fields = ['user__email', 'payment_id']
    raw_id_fields = ['user']
    ordering = ['-created_at']


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ['referrer', 'referred', 'bonus_applied', 'created_at']
    list_filter = ['bonus_applied']
    search_fields = ['referrer__email', 'referred__email']
    raw_id_fields = ['referrer', 'referred', 'subscription']


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ['email', 'code', 'used', 'created_at']
    list_filter = ['used']
    search_fields = ['email']
    ordering = ['-created_at']
