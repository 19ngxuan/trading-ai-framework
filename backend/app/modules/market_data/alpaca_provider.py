from datetime import date
from typing import Any

import httpx

from app.domain.enums import TradingFrequency
from app.modules.market_data.errors import (
    MarketDataProviderError,
    MarketDataUnavailableError,
)
from app.modules.market_data.mapper import alpaca_bar_to_daily_bar
from app.modules.market_data.provider import DailyBar

SUPPORTED_SYMBOL = "SPY"


class AlpacaMarketDataProvider:
    def __init__(
        self,
        *,
        api_key_id: str,
        api_secret_key: str,
        base_url: str = "https://data.alpaca.markets",
        feed: str = "iex",
        adjustment: str = "all",
        timeout_seconds: int = 10,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key_id = api_key_id
        self.api_secret_key = api_secret_key
        self.base_url = base_url.rstrip("/")
        self.feed = feed
        self.adjustment = adjustment
        self.timeout_seconds = timeout_seconds
        self.client = client or httpx.Client(timeout=timeout_seconds)

    def load_range(
        self,
        start_date: date,
        end_date: date,
        symbol: str = SUPPORTED_SYMBOL,
        frequency: TradingFrequency = TradingFrequency.DAILY,
    ) -> list[DailyBar]:
        self._validate_request(symbol, frequency)
        response = self._get(
            f"/v2/stocks/{symbol}/bars",
            params={
                "timeframe": "1Day",
                "start": f"{start_date.isoformat()}T00:00:00Z",
                "end": f"{end_date.isoformat()}T23:59:59Z",
                "adjustment": self.adjustment,
                "feed": self.feed,
            },
        )
        payload = self._json(response)
        bars_payload = payload.get("bars")
        if not isinstance(bars_payload, list):
            raise MarketDataProviderError(
                "Alpaca historical bars response is malformed.",
                details={"payload": payload},
            )
        if not bars_payload:
            raise MarketDataUnavailableError(
                "Alpaca returned no historical bars.",
                details={
                    "symbol": symbol,
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                },
            )

        metadata = {
            "endpoint": f"/v2/stocks/{symbol}/bars",
            "feed": self.feed,
            "adjustment": self.adjustment,
        }
        bars = [
            alpaca_bar_to_daily_bar(item, symbol=symbol, provider_metadata=metadata)
            for item in bars_payload
        ]
        self._validate_bars(bars, start_date, end_date, symbol)
        return sorted(bars, key=lambda bar: bar.date)

    def get_latest_bar(self, symbol: str = SUPPORTED_SYMBOL) -> DailyBar:
        self._validate_request(symbol, TradingFrequency.DAILY)
        response = self._get(
            "/v2/stocks/bars/latest",
            params={"symbols": symbol, "feed": self.feed},
        )
        payload = self._json(response)
        bars_payload = payload.get("bars")
        if not isinstance(bars_payload, dict) or symbol not in bars_payload:
            raise MarketDataUnavailableError(
                "Alpaca returned no latest bar.",
                details={"symbol": symbol},
            )
        return alpaca_bar_to_daily_bar(
            bars_payload[symbol],
            symbol=symbol,
            provider_metadata={
                "endpoint": "/v2/stocks/bars/latest",
                "feed": self.feed,
            },
        )

    def _get(self, path: str, params: dict[str, Any]) -> httpx.Response:
        try:
            response = self.client.get(
                f"{self.base_url}{path}",
                headers={
                    "APCA-API-KEY-ID": self.api_key_id,
                    "APCA-API-SECRET-KEY": self.api_secret_key,
                },
                params=params,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            raise MarketDataProviderError(
                "Alpaca market data request failed.",
                details={
                    "statusCode": exc.response.status_code,
                    "responseText": exc.response.text,
                },
            ) from exc
        except httpx.HTTPError as exc:
            raise MarketDataProviderError(
                "Alpaca market data request failed.",
                details={"error": str(exc)},
            ) from exc

    def _json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise MarketDataProviderError(
                "Alpaca market data response was not valid JSON.",
                details={"responseText": response.text},
            ) from exc
        if not isinstance(payload, dict):
            raise MarketDataProviderError(
                "Alpaca market data response is malformed.",
                details={"payload": payload},
            )
        return payload

    def _validate_request(
        self, symbol: str, frequency: TradingFrequency
    ) -> None:
        if symbol != SUPPORTED_SYMBOL:
            raise MarketDataProviderError(
                "Alpaca market data provider supports SPY only.",
                details={"symbol": symbol},
            )
        if frequency is not TradingFrequency.DAILY:
            raise MarketDataProviderError(
                "Alpaca market data provider supports daily bars only.",
                details={"frequency": frequency.value},
            )

    def _validate_bars(
        self,
        bars: list[DailyBar],
        start_date: date,
        end_date: date,
        symbol: str,
    ) -> None:
        seen_dates: set[date] = set()
        for bar in bars:
            if bar.date in seen_dates:
                raise MarketDataProviderError(
                    "Alpaca returned duplicate bars.",
                    details={"symbol": symbol, "date": bar.date.isoformat()},
                )
            seen_dates.add(bar.date)
            if not start_date <= bar.date <= end_date:
                raise MarketDataProviderError(
                    "Alpaca returned an out-of-range bar.",
                    details={
                        "symbol": symbol,
                        "date": bar.date.isoformat(),
                        "startDate": start_date.isoformat(),
                        "endDate": end_date.isoformat(),
                    },
                )
