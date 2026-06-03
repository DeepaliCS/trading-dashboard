import pytest
from django.urls import reverse
from django.utils import timezone
from trading.models import Trade, Symbol, CTraderCredentials, SyncLog


@pytest.mark.django_db
class TestTradeListView:
    def test_unauthenticated_returns_403(self, api_client):
        response = api_client.get('/api/v1/trades/')
        assert response.status_code in [401, 403]

    def test_authenticated_returns_200(self, auth_client, trade):
        response = auth_client.get('/api/v1/trades/')
        assert response.status_code == 200

    def test_returns_only_user_trades(self, auth_client, trade, user2, symbol):
        Trade.objects.create(
            user=user2, deal_id=999, position_id=999, symbol=symbol,
            direction='SELL', volume='0.1', fill_price='1900.0',
            close_price='1910.0', pnl='10.0', commission='0.5',
            is_closing=True, executed_at=timezone.now(),
        )
        response = auth_client.get('/api/v1/trades/')
        assert response.status_code == 200
        results = response.data['results']
        assert len(results) == 1
        assert results[0]['direction'] == 'BUY'

    def test_filter_by_symbol(self, auth_client, trade):
        response = auth_client.get('/api/v1/trades/?symbol=XAUUSD')
        assert response.status_code == 200
        assert response.data['count'] == 1

    def test_filter_by_symbol_no_match(self, auth_client, trade):
        response = auth_client.get('/api/v1/trades/?symbol=EURUSD')
        assert response.status_code == 200
        assert response.data['count'] == 0

    def test_filter_by_direction(self, auth_client, trade):
        response = auth_client.get('/api/v1/trades/?direction=BUY')
        assert response.status_code == 200
        assert response.data['count'] == 1

    def test_response_contains_expected_fields(self, auth_client, trade):
        response = auth_client.get('/api/v1/trades/')
        result = response.data['results'][0]
        assert 'symbol_name' in result
        assert 'direction' in result
        assert 'pnl' in result
        assert 'net_profit' in result
        assert 'executed_at' in result


@pytest.mark.django_db
class TestTradeDetailView:
    def test_returns_single_trade(self, auth_client, trade):
        response = auth_client.get(f'/api/v1/trades/{trade.pk}/')
        assert response.status_code == 200
        assert response.data['deal_id'] == trade.deal_id

    def test_other_user_cannot_access(self, api_client, user2, trade):
        api_client.force_authenticate(user=user2)
        response = api_client.get(f'/api/v1/trades/{trade.pk}/')
        assert response.status_code == 404


@pytest.mark.django_db
class TestTradeStats:
    def test_returns_stats(self, auth_client, trade):
        response = auth_client.get('/api/v1/trades/stats/')
        assert response.status_code == 200
        assert 'total_trades' in response.data
        assert 'win_rate' in response.data
        assert 'total_pnl' in response.data

    def test_stats_correct_values(self, auth_client, trade):
        response = auth_client.get('/api/v1/trades/stats/')
        assert response.data['total_trades'] == 1
        assert response.data['wins'] == 1
        assert response.data['losses'] == 0
        assert response.data['win_rate'] == 100.0

    def test_unauthenticated_returns_403(self, api_client):
        response = api_client.get('/api/v1/trades/stats/')
        assert response.status_code in [401, 403]


@pytest.mark.django_db
class TestCredentialsView:
    def test_save_credentials(self, auth_client, user):
        response = auth_client.post('/api/v1/credentials/', {
            'client_id': 'test_id',
            'client_secret': 'test_secret',
            'access_token': 'test_token',
            'account_id': 12345678,
            'is_live': False,
        }, format='json')
        assert response.status_code == 201
        assert CTraderCredentials.objects.filter(user=user).exists()

    def test_unauthenticated_cannot_save(self, api_client):
        response = api_client.post('/api/v1/credentials/', {
            'client_id': 'test_id',
            'client_secret': 'test_secret',
            'access_token': 'test_token',
            'account_id': 12345678,
        }, format='json')
        assert response.status_code in [401, 403]


@pytest.mark.django_db
class TestSyncStatus:
    def test_no_sync_log_returns_nulls(self, auth_client):
        response = auth_client.get('/api/v1/sync/status/')
        assert response.status_code == 200
        assert response.data['last_synced_at'] is None

    def test_sync_log_returns_data(self, auth_client, user):
        SyncLog.objects.create(user=user, last_synced_at=timezone.now())
        response = auth_client.get('/api/v1/sync/status/')
        assert response.status_code == 200
        assert response.data['last_synced_at'] is not None

    def test_trigger_sync_without_credentials(self, auth_client):
        response = auth_client.post('/api/v1/sync/')
        assert response.status_code == 400
        assert 'error' in response.data


@pytest.mark.django_db
class TestAnalyticsReport:
    def test_no_trades_returns_404(self, auth_client):
        response = auth_client.get('/api/v1/analytics/report/')
        assert response.status_code == 404

    def test_unauthenticated_returns_403(self, api_client):
        response = api_client.get('/api/v1/analytics/report/')
        assert response.status_code in [401, 403]