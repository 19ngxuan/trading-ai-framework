from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.domain.enums import TradingFrequency
from app.modules.market_data.alpaca_intraday_provider import (
    AlpacaIntradayMarketDataProvider,
)
from app.modules.market_data.errors import (
    MarketDataProviderError,
    MarketDataUnavailableError,
)
from app.modules.market_data.intraday_provider import EXPECTED_BARS_PER_SESSION

NEW_YORK_TZ = ZoneInfo("America/New_York")


def _payload_bar(local_timestamp: datetime, close: str = "100.00") -> dict:
    timestamp = (
        local_timestamp.replace(tzinfo=NEW_YORK_TZ)
        .astimezone(UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )
    close_decimal = Decimal(close)
    return {
        "t": timestamp,
        "o": str(close_decimal - Decimal("0.05")),
        "h": str(close_decimal + Decimal("0.20")),
        "l": str(close_decimal - Decimal("0.20")),
        "c": close,
        "v": "1000",
    }


def _full_session_payload(session_date: date) -> list[dict]:
    timestamp = datetime.combine(session_date, datetime.min.time()).replace(
        hour=9,
        minute=30,
    )
    rows: list[dict] = []
    for index in range(EXPECTED_BARS_PER_SESSION):
        rows.append(_payload_bar(timestamp, close=f"{100 + index / 100:.2f}"))
        timestamp += timedelta(minutes=5)
    return rows


def _provider(handler) -> AlpacaIntradayMarketDataProvider:
    return AlpacaIntradayMarketDataProvider(
        api_key_id="key",
        api_secret_key="secret",
        base_url="https://data.example.test",
        feed="iex",
        adjustment="all",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_alpaca_intraday_provider_maps_paginated_response_and_request() -> None:
    session_rows = _full_session_payload(date(2024, 1, 2))
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if "page_token=next-page" in str(request.url):
            return httpx.Response(200, json={"bars": session_rows[39:]})
        return httpx.Response(
            200,
            json={"bars": session_rows[:39], "next_page_token": "next-page"},
        )

    rows = _provider(handler).load_range(
        date(2024, 1, 2),
        date(2024, 1, 2),
        frequency=TradingFrequency.INTRADAY_5_MIN,
    )

    assert len(rows) == EXPECTED_BARS_PER_SESSION
    assert len(requests) == 2
    first_request = requests[0]
    assert first_request.url.path == "/v2/stocks/SPY/bars"
    assert first_request.headers["APCA-API-KEY-ID"] == "key"
    assert first_request.headers["APCA-API-SECRET-KEY"] == "secret"
    params = dict(first_request.url.params)
    assert params["timeframe"] == "5Min"
    assert params["start"] == "2024-01-02T14:30:00Z"
    assert params["end"] == "2024-01-02T21:00:00Z"
    assert params["adjustment"] == "all"
    assert params["feed"] == "iex"

    assert rows[0].timestamp.isoformat() == "2024-01-02T09:30:00"
    assert rows[-1].timestamp.isoformat() == "2024-01-02T15:55:00"
    assert rows[0].timestamp.tzinfo is None
    assert rows[0].close == Decimal("100.00")
    assert rows[0].raw["provider"] == "alpaca_intraday"
    assert rows[0].raw["metadata"]["timeframe"] == "5Min"
    assert rows[0].raw["payload"]["t"] == session_rows[0]["t"]


def test_alpaca_intraday_provider_ignores_out_of_session_bars() -> None:
    premarket = _payload_bar(datetime(2024, 1, 2, 9, 0), close="99.00")
    after_hours = _payload_bar(datetime(2024, 1, 2, 16, 0), close="101.00")
    provider = _provider(
        lambda _: httpx.Response(
            200,
            json={"bars": [premarket, *_full_session_payload(date(2024, 1, 2)), after_hours]},
        )
    )

    rows = provider.load_range(date(2024, 1, 2), date(2024, 1, 2))

    assert len(rows) == EXPECTED_BARS_PER_SESSION
    assert rows[0].timestamp.hour == 9
    assert rows[0].timestamp.minute == 30
    assert rows[-1].timestamp.hour == 15
    assert rows[-1].timestamp.minute == 55


def test_alpaca_intraday_provider_duplicate_and_missing_bars_are_fatal() -> None:
    full_session = _full_session_payload(date(2024, 1, 2))
    duplicate_provider = _provider(
        lambda _: httpx.Response(200, json={"bars": [*full_session, full_session[0]]})
    )
    with pytest.raises(MarketDataProviderError, match="duplicate"):
        duplicate_provider.load_range(date(2024, 1, 2), date(2024, 1, 2))

    missing_provider = _provider(
        lambda _: httpx.Response(200, json={"bars": full_session[1:]})
    )
    with pytest.raises(MarketDataUnavailableError, match="incomplete"):
        missing_provider.load_range(date(2024, 1, 2), date(2024, 1, 2))


def test_alpaca_intraday_provider_empty_and_malformed_responses_are_fatal() -> None:
    with pytest.raises(MarketDataUnavailableError):
        _provider(lambda _: httpx.Response(200, json={"bars": []})).load_range(
            date(2024, 1, 2),
            date(2024, 1, 2),
        )

    with pytest.raises(MarketDataProviderError):
        _provider(lambda _: httpx.Response(200, json={"bars": [{}]})).load_range(
            date(2024, 1, 2),
            date(2024, 1, 2),
        )


@pytest.mark.parametrize("status_code", [401, 403, 429, 500])
def test_alpaca_intraday_provider_http_errors_raise_provider_error(
    status_code: int,
) -> None:
    provider = _provider(lambda _: httpx.Response(status_code, text="provider error"))

    with pytest.raises(MarketDataProviderError):
        provider.load_range(date(2024, 1, 2), date(2024, 1, 2))


def test_alpaca_intraday_provider_malformed_json_and_timeout_raise_provider_error() -> None:
    malformed = _provider(lambda _: httpx.Response(200, text="{"))
    with pytest.raises(MarketDataProviderError):
        malformed.load_range(date(2024, 1, 2), date(2024, 1, 2))

    def timeout_handler(_: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("forced timeout")

    with pytest.raises(MarketDataProviderError):
        _provider(timeout_handler).load_range(date(2024, 1, 2), date(2024, 1, 2))


def test_alpaca_intraday_provider_rejects_unsupported_symbol_and_frequency() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"bars": []})

    provider = _provider(handler)

    with pytest.raises(MarketDataProviderError):
        provider.load_range(date(2024, 1, 2), date(2024, 1, 2), symbol="QQQ")
    with pytest.raises(MarketDataProviderError):
        provider.load_range(
            date(2024, 1, 2),
            date(2024, 1, 2),
            frequency=TradingFrequency.DAILY,
        )
    assert calls == 0
