from django.urls import path
from .views import ReferralMyView, ReferralListView, ReferralStatsView, PrepareShareView

urlpatterns = [
    path('my/', ReferralMyView.as_view(), name='referral_my'),
    path('list/', ReferralListView.as_view(), name='referral_list'),
    path('stats/', ReferralStatsView.as_view(), name='referral_stats'),
    path('prepare-share/', PrepareShareView.as_view(), name='prepare_share'),
]
