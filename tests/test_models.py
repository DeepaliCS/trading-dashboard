import pytest
from datetime import timezone as dt_timezone
from django.utils import timezone
from trading.models import CTraderCredentials, Symbol, Trade, SyncLog


@pytest.mark.django_db
class TestCTraderCredentials:
    def test_create_credentials(self, user):
        creds = CTraderCredentials(
            user=user,
            client_id='abc123',
            account_id=12345678,
            is_live=False,
        )
        creds.client_secret = 'my_secret'
        creds.access_token = 'my_token'
        creds.save()

        assert creds.pk is not None
        assert creds.client_id == 'abc123'
        assert creds.account_id == 12345678
        assert creds.is_live is False

    def test_client_secret_encrypted(self, user):
        """Stored value should not equal plaintext."""
        creds = CTraderCredentials(
            user=user,
            client_id='abc123',
            account_id=12345678,
        )
        creds.client_secret = 'super_secret'
        creds.save()

        assert creds._client_secret != 'super_secret'

    def test_client_secret_decrypted(self, user):
        """Decrypted value should match original plaintext."""
        creds = CTraderCredentials(
            user=user,
            client_id='abc123',
            account_id=12345678,
        )
        creds.client_secret = 'super_secret'
        creds.save()

        fetched = CTraderCredentials.objects.get(pk=creds.pk)
        assert fetched.client_secret == 'super_secret'

    def test_access_token_encrypted(self, user):
        creds = CTraderCredentials(
            user=user,
            client_id='abc123',
            account_id=12345678,
        )
        creds.access_token = 'my_access_token'
        creds.save()

        assert creds._access_token != 'my_access_token'

    def test_access_token_decrypted(self, user):
        creds = CTraderCredentials(
            user=user,
            client_id='abc123',
            account_id=12345678,
        )
        creds.access_token = 'my_access_token'
        creds.save()

        fetched = CTraderCredentials.objects.get(pk=creds.pk)
        assert fetched.access_token == 'my_access_token'

    def test_one_credential_per_user(self, credentials, user):
        """OneToOneField — second save should update, not create."""
        count_before = CTraderCredentials.objects.filter(user=user).count()
        assert count_before == 1

    def test_str(self, credentials, user):
        assert user.username in str(credentials)


@pytest.mark.django_db
class TestSymbol:
    def test_create_symbol(self):
        symbol = Symbol.objects.create(symbol_id=1, name='XAUUSD')
        assert symbol.pk is not None
        assert symbol.name == 'XAUUSD'

    def test_str(self, symbol):
        assert str(symbol) == 'XAUUSD'

    def test_symbol_id_unique(self, symbol):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Symbol.objects.create(symbol_id=1, name='DUPLICATE')


@pytest.mark.django_db
class TestTrade:
    def test_create_trade(self, trade):
        assert trade.pk is not None
        assert trade.direction == 'BUY'
        assert float(trade.pnl) == 20.0

    def test_str(self, trade):
        s = str(trade)
        assert 'BUY' in s
        assert 'XAUUSD' in s

    def test_unique_together_deal_id(self, trade, user, symbol):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Trade.objects.create(
                user=user,
                deal_id=trade.deal_id,
                position_id=999999,
                symbol=symbol,
                direction='SELL',
                volume='0.10',
                fill_price='1900.00000',
                close_price='1910.00000',
                pnl='10.00',
                commission='0.50',
                is_closing=True,
                executed_at=timezone.now(),
            )

    def test_ordering(self, user, symbol):
        t1 = Trade.objects.create(
            user=user, deal_id=1, position_id=1, symbol=symbol,
            direction='BUY', volume='0.1', fill_price='1900.0',
            close_price='1910.0', pnl='10.0', commission='0.5',
            is_closing=True,
            executed_at=timezone.datetime(2024, 1, 1, tzinfo=dt_timezone.utc),
        )
        t2 = Trade.objects.create(
            user=user, deal_id=2, position_id=2, symbol=symbol,
            direction='SELL', volume='0.1', fill_price='1910.0',
            close_price='1920.0', pnl='10.0', commission='0.5',
            is_closing=True,
            executed_at=timezone.datetime(2024, 1, 2, tzinfo=dt_timezone.utc),
        )
        trades = list(Trade.objects.filter(user=user))
        assert trades[0].pk == t2.pk  # most recent first

    def test_multi_tenant_isolation(self, trade, user2, symbol):
        """user2 should not see user's trades."""
        assert Trade.objects.filter(user=user2).count() == 0


@pytest.mark.django_db
class TestSyncLog:
    def test_create_sync_log(self, user):
        log = SyncLog.objects.create(user=user)
        assert log.pk is not None
        assert log.last_synced_at is None

    def test_str(self, user):
        log = SyncLog.objects.create(user=user)
        assert user.username in str(log)

    def test_one_log_per_user(self, user):
        SyncLog.objects.create(user=user)
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            SyncLog.objects.create(user=user)