import json
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from trading.models import Trade
from dashboard.services.analytics_client import AnalyticsClient


def _trades_to_records(trades):
    """Convert Django Trade queryset to list of dicts for trading-analytics API."""
    return [
        {
            'position_id': t.id,
            'symbol': t.symbol.name,
            'direction': t.direction,
            'volume': float(t.volume),
            'entry_price': float(t.fill_price),
            'close_price': float(t.close_price or t.fill_price),
            'net_profit': float(t.pnl),
            'commission': float(t.commission),
            'swap': 0.0,
            'open_time': str(t.executed_at),
            'close_time': str(t.executed_at),
        }
        for t in trades
    ]


@login_required
def home(request):
    trades = Trade.objects.filter(
        user=request.user, is_closing=True
    ).select_related('symbol').order_by('executed_at')

    recent_trades = trades.order_by('-executed_at')[:25]

    if not trades.exists():
        return render(request, 'dashboard/home.html', {
            'no_data': True,
            'recent_trades': recent_trades,
        })

    records = _trades_to_records(trades)
    client = AnalyticsClient()

    # -- All metrics from trading-analytics --
    metrics = client.get_metrics(records)
    monthly_pnl = client.get_monthly_pnl(records)
    equity_curve = client.get_equity_curve(records)
    by_symbol = client.get_by_symbol(records)
    by_direction = client.get_by_direction(records)

    # -- Build charts from trading-analytics data --
    equity_chart_json = _build_equity_curve(equity_curve)
    monthly_chart_json = _build_monthly_pnl(monthly_pnl)

    return render(request, 'dashboard/home.html', {
        'metrics': metrics,
        'by_symbol': by_symbol,
        'by_direction': by_direction,
        'recent_trades': recent_trades,
        'equity_chart_json': equity_chart_json,
        'monthly_chart_json': monthly_chart_json,
        'analytics_connected': True,
    })


def _build_equity_curve(equity_data: list[dict]):
    """Build Plotly equity curve from trading-analytics data."""
    if not equity_data or 'error' in equity_data[0]:
        return None

    dates = [row['close_time'] for row in equity_data]
    values = [row['equity'] for row in equity_data]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode='lines',
        line=dict(color='#3fb950', width=2),
        fill='tozeroy',
        fillcolor='rgba(63, 185, 80, 0.1)',
        hovertemplate='<b>%{x}</b><br>Equity: %{y:.2f}<extra></extra>',
    ))
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#161b22',
        plot_bgcolor='#161b22',
        font=dict(family='-apple-system, system-ui, sans-serif', color='#e6e6e6'),
        margin=dict(l=40, r=20, t=20, b=40),
        height=380,
        xaxis=dict(gridcolor='#30363d', showgrid=True, zeroline=False),
        yaxis=dict(gridcolor='#30363d', showgrid=True, zeroline=False, title='Equity'),
        hovermode='x unified',
    )
    return json.dumps(fig.to_dict(), cls=PlotlyJSONEncoder)


def _build_monthly_pnl(monthly_data: list[dict]):
    """Build Plotly monthly P&L chart from trading-analytics data."""
    if not monthly_data or 'error' in monthly_data[0]:
        return None

    months = [f"{row['year']}-{str(row['month']).zfill(2)}" for row in monthly_data]
    values = [row['net_profit'] for row in monthly_data]
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