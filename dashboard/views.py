import json

import plotly.graph_objects as go
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum
from django.shortcuts import render
from plotly.utils import PlotlyJSONEncoder

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

    equity_chart_json = _build_equity_curve(trades)
    monthly_chart_json = _build_monthly_pnl(trades)

    return render(request, 'dashboard/home.html', {
        'stats': stats,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'by_symbol': by_symbol,
        'recent_trades': recent_trades,
        'equity_chart_json': equity_chart_json,
        'monthly_chart_json': monthly_chart_json,
    })


def _build_equity_curve(trades):
    """Cumulative P&L over time."""
    rows = trades.order_by('executed_at').values_list('executed_at', 'pnl')
    if not rows:
        return None

    dates = []
    cumulative = []
    running = 0
    for executed_at, pnl in rows:
        running += float(pnl)
        dates.append(executed_at)
        cumulative.append(round(running, 2))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=cumulative,
        mode='lines',
        line=dict(color='#3fb950', width=2),
        fill='tozeroy',
        fillcolor='rgba(63, 185, 80, 0.1)',
        hovertemplate='<b>%{x|%d %b %Y}</b><br>Equity: %{y:.2f}<extra></extra>',
    ))

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#161b22',
        plot_bgcolor='#161b22',
        font=dict(family='-apple-system, system-ui, sans-serif', color='#e6e6e6'),
        margin=dict(l=40, r=20, t=20, b=40),
        height=380,
        xaxis=dict(gridcolor='#30363d', showgrid=True, zeroline=False),
        yaxis=dict(gridcolor='#30363d', showgrid=True, zeroline=False, title='Cumulative P&L'),
        hovermode='x unified',
    )

    return json.dumps(fig.to_dict(), cls=PlotlyJSONEncoder)

def _build_monthly_pnl(trades):
    """Monthly P&L bar chart."""
    from collections import OrderedDict
    rows = trades.order_by('executed_at').values_list('executed_at', 'pnl')
    if not rows:
        return None

    monthly = OrderedDict()
    for executed_at, pnl in rows:
        key = executed_at.strftime('%Y-%m')
        monthly[key] = monthly.get(key, 0) + float(pnl)

    months = list(monthly.keys())
    values = [round(v, 2) for v in monthly.values()]
    colors = ['#3fb950' if v >= 0 else '#f85149' for v in values]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=months,
        y=values,
        marker_color=colors,
        hovertemplate='<b>%{x}</b><br>P&L: %{y:.2f}<extra></extra>',
    ))
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#161b22',
        plot_bgcolor='#161b22',
        font=dict(family='-apple-system, system-ui, sans-serif', color='#e6e6e6'),
        margin=dict(l=40, r=20, t=20, b=40),
        height=300,
        xaxis=dict(gridcolor='#30363d', showgrid=False, zeroline=False),
        yaxis=dict(gridcolor='#30363d', showgrid=True, zeroline=True, zerolinecolor='#30363d', title='P&L'),
    )
    return json.dumps(fig.to_dict(), cls=PlotlyJSONEncoder)