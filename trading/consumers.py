import json
from channels.generic.websocket import AsyncWebsocketConsumer


class PriceTickerConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time spot price streaming.

    Client connects to ws://host/ws/prices/<symbol>/
    Server pushes price updates as JSON.

    Message format:
        {
            "symbol": "XAUUSD",
            "bid": 1900.00,
            "ask": 1900.30,
            "spread": 0.30,
            "timestamp": "2024-01-01T09:00:00Z"
        }
    """

    async def connect(self):
        self.symbol = self.scope['url_route']['kwargs']['symbol'].upper()
        self.group_name = f'prices_{self.symbol}'

        # Join symbol group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'symbol': self.symbol,
            'message': f'Subscribed to {self.symbol} price feed',
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name,
        )

    async def receive(self, text_data):
        """Handle incoming messages from client (e.g. ping)."""
        try:
            data = json.loads(text_data)
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except json.JSONDecodeError:
            pass

    async def price_update(self, event):
        """
        Handler for group messages — broadcasts price to WebSocket client.
        Called when channel_layer.group_send is used with type='price_update'.
        """
        await self.send(text_data=json.dumps({
            'symbol': event['symbol'],
            'bid': event['bid'],
            'ask': event['ask'],
            'spread': event['spread'],
            'timestamp': event['timestamp'],
        }))


class SyncStatusConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time trade sync status updates.

    Client connects to ws://host/ws/sync/<user_id>/
    Server pushes sync progress as JSON.
    """

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f'sync_{self.user.id}'
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

    async def sync_status(self, event):
        """Broadcast sync status update to WebSocket client."""
        await self.send(text_data=json.dumps({
            'type': 'sync_status',
            'status': event['status'],
            'message': event.get('message', ''),
            'trades_synced': event.get('trades_synced', 0),
        }))