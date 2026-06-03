from django.urls import re_path
from trading.consumers import PriceTickerConsumer, SyncStatusConsumer

websocket_urlpatterns = [
    re_path(r'ws/prices/(?P<symbol>\w+)/$', PriceTickerConsumer.as_asgi()),
    re_path(r'ws/sync/(?P<user_id>\d+)/$', SyncStatusConsumer.as_asgi()),
]