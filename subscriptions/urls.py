from django.urls import path
from .views import PlansView, PurchaseView, MySubscriptionView
from .views import webhook_stars, webhook_crypto, webhook_wata

urlpatterns = [
    path('plans/', PlansView.as_view(), name='plans'),
    path('purchase/', PurchaseView.as_view(), name='purchase'),
    path('my/', MySubscriptionView.as_view(), name='my_subscription'),
    path('webhook/stars/', webhook_stars, name='webhook_stars'),
    path('webhook/crypto/', webhook_crypto, name='webhook_crypto'),
    path('webhook/wata/', webhook_wata, name='webhook_wata'),
]
