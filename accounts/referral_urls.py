from django.urls import path
from .views import ReferralMyView, ReferralListView, PrepareShareView

urlpatterns = [
    path('my/', ReferralMyView.as_view(), name='referral_my'),
    path('list/', ReferralListView.as_view(), name='referral_list'),
    path('prepare-share/', PrepareShareView.as_view(), name='prepare_share'),
]
