from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.domain.enums import TradingFrequency
from app.domain.assets import SPY_SYMBOL
from app.domain.assets import is_supported_equity_symbol
from app.domain.assets import normalize_symbol
from app.modules.market_data.errors import (
    MarketDataProviderError,
    MarketDataUnavailableError,
)
from app.modules.market_data.intraday_provider import (
    NEW_YORK_TZ,
    REGULAR_SESSION_END,
    REGULAR_SESSION_START,
    IntradayBar,
)
from app.modules.market_data.intraday_validation import validate_intraday_bars
from app.modules.market_data.intraday_validation import validate_intraday_bars_until
from app.modules.market_data.trading_calendar import (
    TradingCalendar,
    UsEquitiesTradingCalendar,
)

class AlpacaIntradayMarketDataProvider:
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
        trading_calendar: TradingCalendar | None = None,
    ) -> None:
        self.api_key_id = api_key_id
        self.api_secret_key = api_secret_key
        self.base_url = base_url.rstrip("/")
        self.feed = feed
        self.adjustment = adjustment
        self.timeout_seconds = timeout_seconds
        self.client = client or httpx.Client(timeout=timeout_seconds)
        self.trading_calendar = trading_calendar or UsEquitiesTradingCalendar()

    def load_range(
        self,
        start_date: date,
        end_date: date,
        symbol: str = SPY_SYMBOL,
        frequency: TradingFrequency = TradingFrequency.INTRADAY_5_MIN,
    ) -> list[IntradayBar]:
        symbol = normalize_symbol(symbol)
        self._validate_request(symbol, frequency)
        if start_date > end_date:
            raise MarketDataProviderError(
                "start_date must be before or equal to end_date."
            )

        sessions = self.trading_calendar.sessions_between(start_date, end_date)
        bars_payload = self._load_all_pages(symbol, start_date, end_date)
        if not bars_payload and sessions:
            raise MarketDataUnavailableError(
                "Alpaca returned no intraday bars.",
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
            "timeframe": "5Min",
        }
        bars = [
            self._map_bar(item, symbol=symbol, provider_metadata=metadata)
            for item in bars_payload
        ]
        candidate_bars = [
            bar for bar in bars if start_date <= bar.session_date <= end_date
        ]
        validated_bars = validate_intraday_bars(
            bars=candidate_bars,
            sessions=sessions,
            symbol=symbol,
            provider="alpaca_intraday",
        )
        if not validated_bars and sessions:
            raise MarketDataUnavailableError(
                "Alpaca returned no regular-session intraday bars.",
                details={
                    "symbol": symbol,
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                },
            )

        return validated_bars

    def load_session_until(
        self,
        session_date: date,
        through_timestamp: datetime,
        symbol: str = SPY_SYMBOL,
        frequency: TradingFrequency = TradingFrequency.INTRADAY_5_MIN,
    ) -> list[IntradayBar]:
        symbol = normalize_symbol(symbol)
        self._validate_request(symbol, frequency)
        sessions = self.trading_calendar.sessions_between(session_date, session_date)
        if not sessions:
            return []

        bars_payload = self._load_all_pages(symbol, session_date, session_date)
        if not bars_payload:
            raise MarketDataUnavailableError(
                "Alpaca returned no intraday bars through requested bar.",
                details={
                    "symbol": symbol,
                    "sessionDate": session_date.isoformat(),
                    "throughTimestamp": through_timestamp.isoformat(),
                },
            )
        metadata = {
            "endpoint": f"/v2/stocks/{symbol}/bars",
            "feed": self.feed,
            "adjustment": self.adjustment,
            "timeframe": "5Min",
        }
        bars = [
            self._map_bar(item, symbol=symbol, provider_metadata=metadata)
            for item in bars_payload
        ]
        candidate_bars = [
            bar
            for bar in bars
            if bar.session_date == session_date and bar.timestamp <= through_timestamp
        ]
        if not candidate_bars:
            raise MarketDataUnavailableError(
                "Alpaca returned no regular-session intraday bars through requested bar.",
                details={
                    "symbol": symbol,
                    "sessionDate": session_date.isoformat(),
                    "throughTimestamp": through_timestamp.isoformat(),
                },
            )
        return validate_intraday_bars_until(
            bars=candidate_bars,
            session=sessions[0],
            through_timestamp=through_timestamp,
            symbol=symbol,
            provider="alpaca_intraday",
        )

    def _load_all_pages(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        bars: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            params = {
                "timeframe": "5Min",
                "start": self._query_start(start_date),
                "end": self._query_end(end_date),
                "adjustment": self.adjustment,
                "feed": self.feed,
            }
            if page_token:
                params["page_token"] = page_token
            response = self._get(f"/v2/stocks/{symbol}/bars", params=params)
            payload = self._json(response)
            bars_payload = payload.get("bars")
            if not isinstance(bars_payload, list):
                raise MarketDataProviderError(
                    "Alpaca intraday bars response is malformed.",
                    details={"payload": payload},
                )
            bars.extend(bars_payload)
            next_page_token = payload.get("next_page_token")
            if next_page_token is None:
                break
            if not isinstance(next_page_token, str) or not next_page_token:
                raise MarketDataProviderError(
                    "Alpaca intraday pagination token is malformed.",
                    details={"payload": payload},
                )
            page_token = next_page_token
        return bars

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
                "Alpaca intraday market data request failed.",
                details={
                    "statusCode": exc.response.status_code,
                    "responseText": exc.response.text,
                },
            ) from exc
        except httpx.HTTPError as exc:
            raise MarketDataProviderError(
                "Alpaca intraday market data request failed.",
                details={"error": str(exc)},
            ) from exc

    def _json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise MarketDataProviderError(
                "Alpaca intraday market data response was not valid JSON.",
                details={"responseText": response.text},
            ) from exc
        if not isinstance(payload, dict):
            raise MarketDataProviderError(
                "Alpaca intraday market data response is malformed.",
                details={"payload": payload},
            )
        return payload

    def _map_bar(
        self,
        payload: dict[str, Any],
        *,
        symbol: str,
        provider_metadata: dict[str, Any],
    ) -> IntradayBar:
        try:
            timestamp = self._parse_timestamp(payload["t"])
            return IntradayBar(
                timestamp=timestamp,
                session_date=timestamp.date(),
                open=Decimal(str(payload["o"])),
                high=Decimal(str(payload["h"])),
                low=Decimal(str(payload["l"])),
                close=Decimal(str(payload["c"])),
                volume=Decimal(str(payload["v"])),
                raw={
                    "provider": "alpaca_intraday",
                    "symbol": symbol,
                    "metadata": provider_metadata,
                    "timestampLocal": timestamp.isoformat(),
                    "timezone": "America/New_York",
                    "payload": payload,
                },
            )
        except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
            raise MarketDataProviderError(
                "Alpaca intraday market data response could not be mapped.",
                details={"payload": payload, "error": str(exc)},
            ) from exc

    def _parse_timestamp(self, value: str) -> datetime:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            raise ValueError("Alpaca intraday timestamp must include a timezone.")
        return parsed.astimezone(NEW_YORK_TZ).replace(tzinfo=None)

    def _query_start(self, start_date: date) -> str:
        local_start = datetime.combine(
            start_date,
            REGULAR_SESSION_START,
            tzinfo=NEW_YORK_TZ,
        )
        return local_start.astimezone(UTC).isoformat().replace("+00:00", "Z")

    def _query_end(self, end_date: date) -> str:
        local_end = datetime.combine(
            end_date,
            REGULAR_SESSION_END,
            tzinfo=NEW_YORK_TZ,
        )
        return local_end.astimezone(UTC).isoformat().replace("+00:00", "Z")

    def _validate_request(
        self, symbol: str, frequency: TradingFrequency
    ) -> None:
        if not is_supported_equity_symbol(symbol):
            raise MarketDataProviderError(
                "Alpaca intraday market data provider supports configured equity symbols only.",
                details={"symbol": symbol},
            )
        if frequency is not TradingFrequency.INTRADAY_5_MIN:
            raise MarketDataProviderError(
                "Alpaca intraday market data provider supports INTRADAY_5_MIN only.",
                details={"frequency": frequency.value},
            )
