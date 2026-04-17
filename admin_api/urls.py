from django.urls import path
from . import views

urlpatterns = [
    # Dashboard stats
    path('stats/', views.StatsView.as_view()),
    path('stats/chart/registrations/', views.RegistrationChartView.as_view()),
    path('stats/chart/revenue/', views.RevenueChartView.as_view()),
    path('stats/activity-feed/', views.ActivityFeedView.as_view()),
    path('stats/expiring/', views.ExpiringSubsView.as_view()),

    # Users
    path('users/', views.UserListView.as_view()),
    path('users/<int:pk>/', views.UserDetailView.as_view()),
    path('users/<int:pk>/extend/', views.UserExtendView.as_view()),
    path('users/<int:pk>/timeline/', views.UserTimelineView.as_view()),
    path('users/<int:pk>/remnawave/', views.UserRemnawaveView.as_view()),

    # Subscriptions
    path('subscriptions/', views.SubscriptionListView.as_view()),
    path('subscriptions/<int:pk>/manage/', views.SubscriptionManageView.as_view()),

    # Payments
    path('payments/', views.PaymentListView.as_view()),

    # Referrals
    path('referrals/', views.ReferralListView.as_view()),

    # Analytics
    path('analytics/cohorts/', views.CohortAnalysisView.as_view()),
    path('analytics/funnel/', views.FunnelView.as_view()),
    path('analytics/forecast/', views.ForecastView.as_view()),

    # Audit log
    path('audit/', views.AuditLogView.as_view()),

    # System
    path('system/health/', views.SystemHealthView.as_view()),

    # Settings
    path('settings/', views.SettingsView.as_view()),
    path('maintenance/', views.MaintenanceView.as_view()),

    # Search
    path('search/', views.GlobalSearchView.as_view()),

    # Notifications
    path('notifications/send/', views.SendNotificationView.as_view()),
    path('notifications/history/', views.NotificationHistoryView.as_view()),

    # Promo codes
    path('promo/', views.PromoListCreateView.as_view()),
    path('promo/<int:pk>/', views.PromoDetailView.as_view()),

    # Bulk operations
    path('bulk/extend/', views.BulkExtendView.as_view()),

    # Support tickets
    path('tickets/', views.TicketListView.as_view()),
    path('tickets/stats/', views.TicketStatsView.as_view()),
    path('tickets/webhook/', views.TicketWebhookView.as_view()),
    path('tickets/<int:pk>/', views.TicketDetailView.as_view()),
    path('tickets/<int:pk>/reply/', views.TicketReplyView.as_view()),
]
