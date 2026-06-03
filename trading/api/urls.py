from django.urls import path
from trading.api.views import (
    TradeListView,
    TradeDetailView,
    trade_stats,
    CredentialsView,
    trigger_sync,
    sync_status,
    analytics_report,
)

urlpatterns = [
    # Trades
    path('trades/', TradeListView.as_view(), name='trade-list'),
    path('trades/<int:pk>/', TradeDetailView.as_view(), name='trade-detail'),
    path('trades/stats/', trade_stats, name='trade-stats'),

    # Credentials
    path('credentials/', CredentialsView.as_view(), name='credentials'),

    # Sync
    path('sync/', trigger_sync, name='trigger-sync'),
    path('sync/status/', sync_status, name='sync-status'),

    # Analytics
    path('analytics/report/', analytics_report, name='analytics-report'),
]