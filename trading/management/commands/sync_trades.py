import threading
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from twisted.internet import reactor

from trading.models import CTraderCredentials, Symbol, Trade, SyncLog
from ctrader import CTraderClient
from ctrader.models import Credentials
from ctrader_open_api import EndPoints


class Command(BaseCommand):
    help = 'Sync cTrader trades for a user using ctrader-client library'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)

    def handle(self, *args, **opts):
        User = get_user_model()
        try:
            user = User.objects.get(username=opts['username'])
        except User.DoesNotExist:
            raise CommandError(f"User {opts['username']} not found")

        try:
            creds = user.ctrader_credentials
        except CTraderCredentials.DoesNotExist:
            raise CommandError('No cTrader credentials found. Run setup_ctrader first.')

        self.stdout.write('Connecting to cTrader via ctrader-client library...')

        credentials = Credentials(
            client_id=creds.client_id,
            client_secret=creds.client_secret,
            access_token=creds.access_token,
            account_id=creds.account_id,
            host=EndPoints.PROTOBUF_LIVE_HOST if creds.is_live else EndPoints.PROTOBUF_DEMO_HOST,
            port=EndPoints.PROTOBUF_PORT,
        )

        client = CTraderClient(credentials)
        result = {'done': False, 'error': None}

        def on_ready(c):
            self.stdout.write('Authenticated ✓ — fetching symbols...')

            def on_symbols(symbol_map):
                # Save symbols to DB
                for symbol_id, symbol_name in symbol_map.items():
                    Symbol.objects.update_or_create(
                        symbol_id=symbol_id,
                        defaults={'name': symbol_name},
                    )
                self.stdout.write(f'Symbols saved: {len(symbol_map)} ✓')
                self._fetch_trades(c, user, creds, result)

            d = c.fetch_symbols()
            d.addCallback(on_symbols)
            d.addErrback(on_error)

        def on_error(failure):
            result['error'] = str(failure)
            result['done'] = True
            if reactor.running:
                reactor.stop()

        def on_trades(trades):
            self.stdout.write(f'Fetched {len(trades)} trades — saving to DB...')
            from django.utils import timezone
            from decimal import Decimal

            saved = 0
            for trade in trades:
                symbol = Symbol.objects.filter(symbol_id=trade.symbol_id).first()
                if not symbol:
                    continue
                _, created = Trade.objects.update_or_create(
                    user=user,
                    deal_id=trade.position_id,
                    defaults={
                        'position_id': trade.position_id,
                        'symbol': symbol,
                        'direction': trade.direction,
                        'volume': Decimal(str(trade.volume)),
                        'fill_price': Decimal(str(trade.entry_price)),
                        'close_price': Decimal(str(trade.close_price)),
                        'pnl': Decimal(str(trade.net_profit)),
                        'commission': Decimal(str(trade.commission)),
                        'is_closing': True,
                        'executed_at': trade.close_time,
                    }
                )
                if created:
                    saved += 1

            SyncLog.objects.update_or_create(
                user=user,
                defaults={'last_synced_at': timezone.now()},
            )

            self.stdout.write(self.style.SUCCESS(
                f'Sync complete — {saved} new trades saved ✓'
            ))
            result['done'] = True
            if reactor.running:
                reactor.stop()

        self._on_trades = on_trades

        client.connect(on_ready=on_ready, on_disconnected=lambda r: None)
        client._on_trades_callback = on_trades

        def run_reactor():
            reactor.run(installSignalHandlers=False)

        thread = threading.Thread(target=run_reactor)
        thread.start()
        thread.join(timeout=300)

        if result.get('error'):
            raise CommandError(f"Sync failed: {result['error']}")

    def _fetch_trades(self, client, user, creds, result):
        from datetime import datetime, timezone
        from trading.models import SyncLog

        sync_log = SyncLog.objects.filter(user=user).first()
        from_dt = sync_log.last_synced_at if sync_log and sync_log.last_synced_at else datetime(2020, 1, 1, tzinfo=timezone.utc)
        to_dt = datetime.now(timezone.utc)

        self.stdout.write(f'Fetching trades from {from_dt} to {to_dt}...')

        client.fetch_trades(
            from_dt=from_dt,
            to_dt=to_dt,
            on_trades=self._on_trades,
        )