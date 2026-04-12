from django.urls import path
from .views import PlansView, PurchaseView, MySubscriptionView, TrialActivateView, TrialUpgradeView
from .views import webhook_stars, webhook_crypto, webhook_wata

urlpatterns = [
    path('plans/', PlansView.as_view(), name='plans'),
    path('purchase/', PurchaseView.as_view(), name='purchase'),
    path('my/', MySubscriptionView.as_view(), name='my_subscription'),
    path('trial/', TrialActivateView.as_view(), name='trial'),
    path('trial-upgrade/', TrialUpgradeView.as_view(), name='trial_upgrade'),
    path('webhook/stars/', webhook_stars, name='webhook_stars'),
    path('webhook/crypto/', webhook_crypto, name='webhook_crypto'),
    path('webhook/wata/', webhook_wata, name='webhook_wata'),
]
