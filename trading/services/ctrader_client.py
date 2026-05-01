"""
cTrader Open API client — Django-integrated.

Twisted reactor lifecycle: we run the reactor inside the management command,
not in a Django request. For web requests later, we'll use a Celery task.
"""
import calendar
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ctrader_open_api import Client, EndPoints, Protobuf, TcpProtocol
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *
from twisted.internet import defer, reactor

from trading.models import Symbol, SyncLog, Trade

# cTrader API max range per dealList request — 1 week
CHUNK_DAYS = 7


def _to_ms(dt: datetime) -> int:
    return int(calendar.timegm(dt.utctimetuple()) * 1000)


def _from_ms(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


class CTraderSync:
    """
    Syncs trades + symbols for one user.

    Usage (inside a Twisted reactor context):
        sync = CTraderSync(user, credentials)
        sync.run()
    """

    def __init__(self, user, credentials, host=None):
        self.user = user
        self.creds = credentials
        self.host = host or (
            EndPoints.PROTOBUF_LIVE_HOST if credentials.is_live
            else EndPoints.PROTOBUF_DEMO_HOST
        )
        self.client = Client(self.host, EndPoints.PROTOBUF_PORT, TcpProtocol)
        self.symbols_cache = {}
        self.deferred_done = defer.Deferred()

    # ------------- entry point -------------

    def run(self):
        self.client.setConnectedCallback(self._on_connected)
        self.client.setDisconnectedCallback(self._on_disconnected)
        self.client.setMessageReceivedCallback(self._on_message)
        self.client.startService()
        return self.deferred_done

    # ------------- callbacks -------------

    def _on_connected(self, client):
        req = ProtoOAApplicationAuthReq()
        req.clientId = self.creds.client_id
        req.clientSecret = self.creds.client_secret
        d = client.send(req)
        d.addErrback(self._fail)

    def _on_disconnected(self, client, reason):
        if not self.deferred_done.called:
            self.deferred_done.errback(Exception(f'Disconnected: {reason}'))

    def _on_message(self, client, message):
        msg = Protobuf.extract(message)
        name = msg.__class__.__name__

        if name == 'ProtoOAApplicationAuthRes':
            self._auth_account()
        elif name == 'ProtoOAAccountAuthRes':
            self._fetch_symbols()
        elif name == 'ProtoOASymbolsListRes':
            self._save_symbols(msg)
            self._fetch_deals_chunked()
        elif name == 'ProtoOADealListRes':
            self._handle_deals_chunk(msg)
        elif name == 'ProtoOAErrorRes':
            self._fail(Exception(f'cTrader error: {msg.description}'))

    # ------------- flow steps -------------

    def _auth_account(self):
        req = ProtoOAAccountAuthReq()
        req.ctidTraderAccountId = self.creds.account_id
        req.accessToken = self.creds.access_token
        self.client.send(req).addErrback(self._fail)

    def _fetch_symbols(self):
        req = ProtoOASymbolsListReq()
        req.ctidTraderAccountId = self.creds.account_id
        req.includeArchivedSymbols = False
        self.client.send(req).addErrback(self._fail)

    def _save_symbols(self, msg):
        from django.db import transaction
        with transaction.atomic():
            for s in msg.symbol:
                obj, _ = Symbol.objects.update_or_create(
                    symbol_id=s.symbolId,
                    defaults={'name': s.symbolName},
                )
                self.symbols_cache[s.symbolId] = obj

    def _fetch_deals_chunked(self):
        sync_log, _ = SyncLog.objects.get_or_create(user=self.user)
        start = sync_log.last_synced_at or (datetime.now(timezone.utc) - timedelta(days=365))
        end = datetime.now(timezone.utc)

        self._chunks = []
        cursor = start
        while cursor < end:
            chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), end)
            self._chunks.append((cursor, chunk_end))
            cursor = chunk_end

        self._final_end = end
        self._next_chunk()

    def _next_chunk(self):
        if not self._chunks:
            self._finish()
            return
        start, end = self._chunks.pop(0)
        req = ProtoOADealListReq()
        req.ctidTraderAccountId = self.creds.account_id
        req.fromTimestamp = _to_ms(start)
        req.toTimestamp = _to_ms(end)
        self.client.send(req).addErrback(self._fail)

    def _handle_deals_chunk(self, msg):
        from django.db import transaction
        with transaction.atomic():
            for deal in msg.deal:
                if not deal.closePositionDetail.ByteSize() and not deal.dealStatus:
                    continue
                symbol = self.symbols_cache.get(deal.symbolId)
                if not symbol:
                    continue
                close_price = (
                    Decimal(str(deal.closePositionDetail.entryPrice))
                    if deal.closePositionDetail.ByteSize() else None
                )
                Trade.objects.update_or_create(
                    user=self.user,
                    deal_id=deal.dealId,
                    defaults={
                        'position_id': deal.positionId,
                        'symbol': symbol,
                        'direction': 'BUY' if deal.tradeSide == 1 else 'SELL',
                        'volume': Decimal(str(deal.volume / 100)),
                        'fill_price': Decimal(str(deal.executionPrice)),
                        'close_price': close_price,
                        'pnl': Decimal(str(deal.closePositionDetail.grossProfit / 100))
                            if deal.closePositionDetail.ByteSize() else Decimal('0'),
                        'commission': Decimal(str(deal.commission / 100)),
                        'is_closing': bool(deal.closePositionDetail.ByteSize()),
                        'executed_at': _from_ms(deal.executionTimestamp),
                    },
                )
        self._next_chunk()

    def _finish(self):
        SyncLog.objects.update_or_create(
            user=self.user,
            defaults={'last_synced_at': self._final_end},
        )
        self.client.stopService()
        if not self.deferred_done.called:
            self.deferred_done.callback(True)

    def _fail(self, failure):
        self.client.stopService()
        if not self.deferred_done.called:
            self.deferred_done.errback(failure)
