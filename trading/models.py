from django.conf import settings
from django.db import models

from .encryption import encrypt, decrypt


class CTraderCredentials(models.Model):
    """Per-user encrypted cTrader API credentials."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ctrader_credentials',
    )
    client_id = models.CharField(max_length=255)
    _client_secret = models.TextField(db_column='client_secret')
    _access_token = models.TextField(db_column='access_token')
    account_id = models.BigIntegerField()
    is_live = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def client_secret(self):
        return decrypt(self._client_secret)

    @client_secret.setter
    def client_secret(self, value):
        self._client_secret = encrypt(value)

    @property
    def access_token(self):
        return decrypt(self._access_token)

    @access_token.setter
    def access_token(self, value):
        self._access_token = encrypt(value)

    def __str__(self):
        return f'cTrader creds for {self.user.username}'


class Symbol(models.Model):
    """cTrader symbol mapping (id -> name like XAUUSD)."""
    symbol_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Trade(models.Model):
    """A closed trade (deal) from cTrader."""
    DIRECTION_CHOICES = [('BUY', 'Buy'), ('SELL', 'Sell')]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trades',
    )
    deal_id = models.BigIntegerField()
    position_id = models.BigIntegerField()
    symbol = models.ForeignKey(Symbol, on_delete=models.PROTECT)
    direction = models.CharField(max_length=4, choices=DIRECTION_CHOICES)
    volume = models.DecimalField(max_digits=18, decimal_places=2)
    fill_price = models.DecimalField(max_digits=18, decimal_places=5)
    close_price = models.DecimalField(max_digits=18, decimal_places=5, null=True, blank=True)
    pnl = models.DecimalField(max_digits=18, decimal_places=2)
    commission = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    is_closing = models.BooleanField(default=True)
    executed_at = models.DateTimeField()
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'deal_id')]
        indexes = [
            models.Index(fields=['user', '-executed_at']),
            models.Index(fields=['user', 'symbol']),
        ]
        ordering = ['-executed_at']

    def __str__(self):
        return f'{self.direction} {self.volume} {self.symbol} @ {self.fill_price}'


class SyncLog(models.Model):
    """Tracks last successful sync per user — for incremental fetching."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sync_log',
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Sync log for {self.user.username}'