from django.urls import path
from .views import (
    PlansView, PurchaseView, MySubscriptionView, TrialActivateView, TrialUpgradeView,
    ExchangeRatesView, ValidatePromoView, ActivateGiftView, PromoInfoView, UserDevicesView,
    UpgradePreviewView, UpgradeView, PaymentHistoryView,
    webhook_stars, webhook_crypto, webhook_wata,
)

urlpatterns = [
    path('plans/', PlansView.as_view(), name='plans'),
    path('purchase/', PurchaseView.as_view(), name='purchase'),
    path('my/', MySubscriptionView.as_view(), name='my_subscription'),
    path('trial/', TrialActivateView.as_view(), name='trial'),
    path('trial-upgrade/', TrialUpgradeView.as_view(), name='trial_upgrade'),
    path('rates/', ExchangeRatesView.as_view(), name='exchange_rates'),
    path('devices/', UserDevicesView.as_view(), name='user_devices'),
    path('validate-promo/', ValidatePromoView.as_view(), name='validate_promo'),
    path('activate-gift/', ActivateGiftView.as_view(), name='activate_gift'),
    path('promo-info/', PromoInfoView.as_view(), name='promo_info'),
    path('upgrade-preview/', UpgradePreviewView.as_view(), name='upgrade_preview'),
    path('upgrade/', UpgradeView.as_view(), name='upgrade'),
    path('history/', PaymentHistoryView.as_view(), name='payment_history'),
    path('webhook/stars/', webhook_stars, name='webhook_stars'),
    path('webhook/crypto/', webhook_crypto, name='webhook_crypto'),
    path('webhook/wata/', webhook_wata, name='webhook_wata'),
]
