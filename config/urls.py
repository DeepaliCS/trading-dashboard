from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Google OAuth + allauth
    path('accounts/', include('allauth.urls')),

    # Dashboard (Plotly charts, HTML views)
    path('dashboard/', include('dashboard.urls')),

    # Trading REST API
    path('api/v1/', include('trading.api.urls')),

    # Root redirect
    path('', include('dashboard.urls')),
]