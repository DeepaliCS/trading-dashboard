import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

celery_app = Celery('trading_dashboard')
celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.autodiscover_tasks()


@celery_app.task(bind=True, name='trading.sync_trades')
def sync_trades_task(self, user_id: int) -> dict:
    """
    Async Celery task — sync trades for a user from cTrader API.
    Runs the existing CTraderSync in a Twisted reactor thread.
    """
    import django
    django.setup()

    from django.contrib.auth import get_user_model
    from trading.models import CTraderCredentials, SyncLog
    from trading.services.ctrader_client import CTraderSync
    from twisted.internet import reactor, defer
    import threading

    User = get_user_model()

    try:
        user = User.objects.get(pk=user_id)
        credentials = CTraderCredentials.objects.get(user=user)
    except (User.DoesNotExist, CTraderCredentials.DoesNotExist) as e:
        return {'status': 'error', 'message': str(e)}

    result = {'status': 'pending'}

    def run_sync():
        sync = CTraderSync(user, credentials)
        d = sync.run()

        def on_success(res):
            result['status'] = 'success'
            reactor.stop()

        def on_failure(failure):
            result['status'] = 'error'
            result['message'] = str(failure)
            reactor.stop()

        d.addCallbacks(on_success, on_failure)

    reactor.callWhenRunning(run_sync)

    thread = threading.Thread(target=reactor.run, kwargs={'installSignalHandlers': False})
    thread.start()
    thread.join(timeout=300)  # 5 min timeout

    return result


@celery_app.task(name='trading.calculate_metrics')
def calculate_metrics_task(user_id: int) -> dict:
    """
    Async Celery task — fetch user trades and post to trading-analytics API.
    Returns full strategy report.
    """
    import django
    django.setup()

    from django.contrib.auth import get_user_model
    from trading.models import Trade
    from dashboard.services.analytics_client import AnalyticsClient

    User = get_user_model()

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist as e:
        return {'status': 'error', 'message': str(e)}

    trades = Trade.objects.filter(
        user=user, is_closing=True
    ).select_related('symbol').values(
        'id', 'symbol__name', 'direction', 'volume',
        'fill_price', 'close_price', 'pnl',
        'commission', 'executed_at',
    )

    records = [
        {
            'position_id': t['id'],
            'symbol': t['symbol__name'],
            'direction': t['direction'],
            'volume': float(t['volume']),
            'entry_price': float(t['fill_price']),
            'close_price': float(t['close_price'] or t['fill_price']),
            'net_profit': float(t['pnl']),
            'commission': float(t['commission']),
            'swap': 0.0,
            'open_time': str(t['executed_at']),
            'close_time': str(t['executed_at']),
        }
        for t in trades
    ]

    client = AnalyticsClient()
    return client.get_report(records)