from rest_framework import serializers
from trading.models import CTraderCredentials, Symbol, Trade, SyncLog


class SymbolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Symbol
        fields = ['id', 'symbol_id', 'name']


class TradeSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source='symbol.name', read_only=True)
    net_profit = serializers.SerializerMethodField()

    class Meta:
        model = Trade
        fields = [
            'id',
            'deal_id',
            'position_id',
            'symbol_name',
            'direction',
            'volume',
            'fill_price',
            'close_price',
            'pnl',
            'net_profit',
            'commission',
            'is_closing',
            'executed_at',
            'synced_at',
        ]

    def get_net_profit(self, obj) -> float:
        return float(obj.pnl) - abs(float(obj.commission))


class CTraderCredentialsSerializer(serializers.ModelSerializer):
    """Write-only serializer — never exposes decrypted secrets."""
    client_secret = serializers.CharField(write_only=True)
    access_token = serializers.CharField(write_only=True)

    class Meta:
        model = CTraderCredentials
        fields = [
            'id',
            'client_id',
            'client_secret',
            'access_token',
            'account_id',
            'is_live',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        user = self.context['request'].user
        creds, _ = CTraderCredentials.objects.update_or_create(
            user=user,
            defaults={
                'client_id': validated_data['client_id'],
                'account_id': validated_data['account_id'],
                'is_live': validated_data.get('is_live', False),
            }
        )
        creds.client_secret = validated_data['client_secret']
        creds.access_token = validated_data['access_token']
        creds.save()
        return creds


class SyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncLog
        fields = ['id', 'last_synced_at', 'last_run_at']


class TradeStatsSerializer(serializers.Serializer):
    """Summary stats for the dashboard."""
    total_trades = serializers.IntegerField()
    total_pnl = serializers.DecimalField(max_digits=18, decimal_places=2)
    avg_pnl = serializers.DecimalField(max_digits=18, decimal_places=2)
    wins = serializers.IntegerField()
    losses = serializers.IntegerField()
    win_rate = serializers.FloatField()