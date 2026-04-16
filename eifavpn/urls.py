from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def maintenance_view(request):
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/maintenance/', maintenance_view),
    path('api/auth/', include('accounts.urls')),
    path('api/referral/', include('accounts.referral_urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
    path('api/admin/', include('admin_api.urls')),
    path('api/', include('api.urls')),
]
