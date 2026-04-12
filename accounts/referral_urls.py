from django.urls import path
from .views import ReferralMyView, ReferralListView

urlpatterns = [
    path('my/', ReferralMyView.as_view(), name='referral_my'),
    path('list/', ReferralListView.as_view(), name='referral_list'),
]
