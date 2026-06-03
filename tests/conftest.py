import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def user(db):
    User = get_user_model()
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
    )


@pytest.fixture
def user2(db):
    User = get_user_model()
    return User.objects.create_user(
        username='testuser2',
        email='test2@example.com',
        password='testpass123',
    )


@pytest.fixture
def credentials(db, user):
    from trading.models import CTraderCredentials
    creds = CTraderCredentials(
        user=user,
        client_id='test_client_id',
        account_id=12345678,
        is_live=False,
    )
    creds.client_secret = 'test_secret'
    creds.access_token = 'test_token'
    creds.save()
    return creds


@pytest.fixture
def symbol(db):
    from trading.models import Symbol
    return Symbol.objects.create(symbol_id=1, name='XAUUSD')


@pytest.fixture
def trade(db, user, symbol):
    from trading.models import Trade
    from django.utils import timezone
    return Trade.objects.create(
        user=user,
        deal_id=100001,
        position_id=200001,
        symbol=symbol,
        direction='BUY',
        volume='0.10',
        fill_price='1900.00000',
        close_price='1920.00000',
        pnl='20.00',
        commission='0.50',
        is_closing=True,
        executed_at=timezone.now(),
    )


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client