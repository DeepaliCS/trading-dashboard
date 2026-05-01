from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum
from django.shortcuts import render

from trading.models import Trade


@login_required
def home(request):
    trades = Trade.objects.filter(user=request.user, is_closing=True)

    stats = trades.aggregate(
        total_trades=Count('id'),
        total_pnl=Sum('pnl'),
        avg_pnl=Avg('pnl'),
    )
    wins = trades.filter(pnl__gt=0).count()
    losses = trades.filter(pnl__lt=0).count()
    win_rate = (wins / stats['total_trades'] * 100) if stats['total_trades'] else 0

    by_symbol = (
        trades.values('symbol__name')
        .annotate(trade_count=Count('id'), total_pnl=Sum('pnl'))
        .order_by('-total_pnl')
    )

    recent_trades = trades.select_related('symbol').order_by('-executed_at')[:25]

    return render(request, 'dashboard/home.html', {
        'stats': stats,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'by_symbol': by_symbol,
        'recent_trades': recent_trades,
    })