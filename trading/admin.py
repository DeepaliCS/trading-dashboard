from django.contrib import admin

from .models import CTraderCredentials, Symbol, SyncLog, Trade


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ('executed_at', 'user', 'symbol', 'direction', 'volume', 'fill_price', 'pnl', 'is_closing')
    list_filter = ('direction', 'is_closing', 'symbol', 'user')
    search_fields = ('symbol__name', 'deal_id', 'position_id')
    date_hierarchy = 'executed_at'
    readonly_fields = ('synced_at',)


@admin.register(Symbol)
class SymbolAdmin(admin.ModelAdmin):
    list_display = ('symbol_id', 'name')
    search_fields = ('name',)


@admin.register(CTraderCredentials)
class CTraderCredentialsAdmin(admin.ModelAdmin):
    list_display = ('user', 'account_id', 'is_live', 'updated_at')
    readonly_fields = ('created_at', 'updated_at', '_client_secret', '_access_token')


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'last_synced_at', 'last_run_at')
    readonly_fields = ('last_run_at',)
