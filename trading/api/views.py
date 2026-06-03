
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from trading.models import CTraderCredentials, SyncLog, Trade
from trading.api.serializers import (
    CTraderCredentialsSerializer,
    SyncLogSerializer,
    TradeSerializer,
)


# ------------------------------------------------------------------
# Trades
# ------------------------------------------------------------------

class TradeListView(generics.ListAPIView):
    """
    GET /api/v1/trades/
    Returns paginated list of closed trades for the authenticated user.
    Supports filtering by symbol and direction via query params.
    """
    serializer_class = TradeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Trade.objects.filter(
            user=self.request.user,
            is_closing=True,
        ).select_related('symbol').order_by('-executed_at')

        symbol = self.request.query_params.get('symbol')
        direction = self.request.query_params.get('direction')

        if symbol:
            qs = qs.filter(symbol__name__iexact=symbol)
        if direction:
            qs = qs.filter(direction__iexact=direction)

        return qs


class TradeDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/trades/<id>/
    Returns a single trade for the authenticated user.
    """
    serializer_class = TradeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Trade.objects.filter(
            user=self.request.user,
        ).select_related('symbol')


# ------------------------------------------------------------------
# Stats
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trade_stats(request):
    """
    GET /api/v1/trades/stats/
    Returns summary stats from trading-analytics service.
    """
    from dashboard.services.analytics_client import AnalyticsClient
    from dashboard.views import _trades_to_records

    trades = Trade.objects.filter(
        user=request.user, is_closing=True
    ).select_related('symbol')

    if not trades.exists():
        return Response({'error': 'No trades found.'}, status=status.HTTP_404_NOT_FOUND)

    records = _trades_to_records(trades)
    client = AnalyticsClient()
    metrics = client.get_metrics(records)

    if 'error' in metrics:
        return Response(metrics, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(metrics)



# ------------------------------------------------------------------
# Credentials
# ------------------------------------------------------------------

class CredentialsView(generics.CreateAPIView):
    """
    POST /api/v1/credentials/
    Save or update encrypted cTrader credentials for the authenticated user.
    """
    serializer_class = CTraderCredentialsSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        return {'request': self.request}


# ------------------------------------------------------------------
# Sync
# ------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_sync(request):
    """
    POST /api/v1/sync/
    Trigger an async Celery task to sync trades from cTrader API.
    """
    try:
        CTraderCredentials.objects.get(user=request.user)
    except CTraderCredentials.DoesNotExist:
        return Response(
            {'error': 'No cTrader credentials found. Please add credentials first.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from trading.tasks import sync_trades_task
    task = sync_trades_task.delay(request.user.id)

    return Response({
        'status': 'queued',
        'task_id': task.id,
        'message': 'Trade sync started. Check /api/v1/sync/status/ for progress.',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sync_status(request):
    """
    GET /api/v1/sync/status/
    Returns the last sync log for the authenticated user.
    """
    try:
        sync_log = SyncLog.objects.get(user=request.user)
        serializer = SyncLogSerializer(sync_log)
        return Response(serializer.data)
    except SyncLog.DoesNotExist:
        return Response({'last_synced_at': None, 'last_run_at': None})


# ------------------------------------------------------------------
# Analytics (calls trading-analytics API)
# ------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_report(request):
    """
    GET /api/v1/analytics/report/
    Fetches full strategy report from trading-analytics service.
    """
    from dashboard.services.analytics_client import AnalyticsClient

    trades = Trade.objects.filter(
        user=request.user, is_closing=True
    ).select_related('symbol')

    if not trades.exists():
        return Response(
            {'error': 'No trades found. Sync your account first.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    records = [
        {
            'position_id': t.id,
            'symbol': t.symbol.name,
            'direction': t.direction,
            'volume': float(t.volume),
            'entry_price': float(t.fill_price),
            'close_price': float(t.close_price or t.fill_price),
            'net_profit': float(t.pnl),
            'commission': float(t.commission),
            'swap': 0.0,
            'open_time': str(t.executed_at),
            'close_time': str(t.executed_at),
        }
        for t in trades
    ]

    client = AnalyticsClient()
    report = client.get_report(records)

    if 'error' in report:
        return Response(report, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(report)