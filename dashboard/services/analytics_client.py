import httpx
from django.conf import settings


class AnalyticsClient:
    """
    HTTP client for the trading-analytics FastAPI service.

    Calls the trading-analytics API to calculate performance metrics,
    generate reports, and fetch equity curve data.

    Base URL configured via ANALYTICS_API_URL in settings.py.
    Default: http://localhost:8001/api/v1
    """

    def __init__(self):
        self.base_url = settings.ANALYTICS_API_URL
        self.timeout = 30.0

    def _build_payload(
        self,
        records: list[dict],
        starting_balance: float = 10000.0,
    ) -> dict:
        return {
            "trades": records,
            "starting_balance": starting_balance,
        }

    def get_metrics(
        self,
        records: list[dict],
        starting_balance: float = 10000.0,
    ) -> dict:
        """
        POST /metrics
        Returns overall PerformanceMetrics for a set of trades.
        """
        try:
            response = httpx.post(
                f"{self.base_url}/metrics",
                json=self._build_payload(records, starting_balance),
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {"error": f"Analytics API error: {str(e)}"}

    def get_report(
        self,
        records: list[dict],
        starting_balance: float = 10000.0,
    ) -> dict:
        """
        POST /report
        Returns full StrategyReport including monthly PnL, equity curve,
        breakdowns by symbol and direction.
        """
        try:
            response = httpx.post(
                f"{self.base_url}/report",
                json=self._build_payload(records, starting_balance),
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {"error": f"Analytics API error: {str(e)}"}

    def get_equity_curve(
        self,
        records: list[dict],
        starting_balance: float = 10000.0,
    ) -> list[dict]:
        """
        POST /equity-curve
        Returns list of {close_time, equity} data points for charting.
        """
        try:
            response = httpx.post(
                f"{self.base_url}/equity-curve",
                json=self._build_payload(records, starting_balance),
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return [{"error": f"Analytics API error: {str(e)}"}]

    def get_monthly_pnl(
        self,
        records: list[dict],
        starting_balance: float = 10000.0,
    ) -> list[dict]:
        """
        POST /monthly-pnl
        Returns list of {year, month, net_profit, trade_count}.
        """
        try:
            response = httpx.post(
                f"{self.base_url}/monthly-pnl",
                json=self._build_payload(records, starting_balance),
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return [{"error": f"Analytics API error: {str(e)}"}]

    def get_by_symbol(
        self,
        records: list[dict],
        starting_balance: float = 10000.0,
    ) -> dict:
        """
        POST /by-symbol
        Returns metrics broken down by symbol.
        """
        try:
            response = httpx.post(
                f"{self.base_url}/by-symbol",
                json=self._build_payload(records, starting_balance),
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {"error": f"Analytics API error: {str(e)}"}

    def get_by_direction(
        self,
        records: list[dict],
        starting_balance: float = 10000.0,
    ) -> dict:
        """
        POST /by-direction
        Returns metrics broken down by BUY/SELL.
        """
        try:
            response = httpx.post(
                f"{self.base_url}/by-direction",
                json=self._build_payload(records, starting_balance),
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {"error": f"Analytics API error: {str(e)}"}

    def ping(self) -> bool:
        """Check if trading-analytics API is reachable."""
        try:
            response = httpx.get(
                f"{self.base_url}/ping",
                timeout=5.0,
            )
            return response.status_code == 200
        except httpx.HTTPError:
            return False