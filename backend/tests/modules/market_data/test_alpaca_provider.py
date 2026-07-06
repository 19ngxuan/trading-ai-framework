from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.domain.enums import TradingFrequency
from app.modules.market_data.alpaca_provider import AlpacaMarketDataProvider
from app.modules.market_data.errors import (
    MarketDataProviderError,
    MarketDataUnavailableError,
)


def _provider(handler) -> AlpacaMarketDataProvider:
    return AlpacaMarketDataProvider(
        api_key_id="key",
        api_secret_key="secret",
        base_url="https://data.example.test",
        feed="iex",
        adjustment="all",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_alpaca_provider_maps_historical_response_and_request() -> None:
    seen_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return httpx.Response(
            200,
            json={
                "bars": [
                    {
                        "t": "2024-01-03T05:00:00Z",
                        "o": 472.0,
                        "h": 474.0,
                        "l": 470.0,
                        "c": 472.0,
                        "v": 1001,
                    },
                    {
                        "t": "2024-01-02T05:00:00Z",
                        "o": 470.0,
                        "h": 472.0,
                        "l": 469.0,
                        "c": 471.0,
                        "v": 1000,
                    },
                ]
            },
        )

    rows = _provider(handler).load_range(
        date(2024, 1, 2),
        date(2024, 1, 3),
        symbol="AAPL",
    )

    assert seen_request is not None
    assert seen_request.url.path == "/v2/stocks/AAPL/bars"
    assert seen_request.headers["APCA-API-KEY-ID"] == "key"
    assert seen_request.headers["APCA-API-SECRET-KEY"] == "secret"
    params = dict(seen_request.url.params)
    assert params["timeframe"] == "1Day"
    assert params["start"] == "2024-01-02T00:00:00Z"
    assert params["end"] == "2024-01-03T23:59:59Z"
    assert params["adjustment"] == "all"
    assert params["feed"] == "iex"

    assert [row.date for row in rows] == [date(2024, 1, 2), date(2024, 1, 3)]
    assert rows[0].open == Decimal("470.0")
    assert rows[0].adjusted_close == Decimal("471.0")
    assert rows[0].volume == Decimal("1000")
    assert rows[0].raw["provider"] == "alpaca"
    assert rows[0].raw["payload"]["c"] == 471.0


def test_alpaca_provider_maps_latest_bar() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/stocks/bars/latest"
        assert dict(request.url.params)["symbols"] == "MSFT"
        return httpx.Response(
            200,
            json={
                "bars": {
                    "MSFT": {
                        "t": "2024-01-05T05:00:00Z",
                        "o": "473.00",
                        "h": "475.00",
                        "l": "472.00",
                        "c": "474.00",
                        "v": "1004",
                    }
                }
            },
        )

    row = _provider(handler).get_latest_bar("MSFT")

    assert row.date == date(2024, 1, 5)
    assert row.adjusted_close == Decimal("474.00")
    assert row.raw["metadata"]["endpoint"] == "/v2/stocks/bars/latest"


def test_alpaca_provider_empty_bars_raise_unavailable() -> None:
    provider = _provider(lambda _: httpx.Response(200, json={"bars": []}))

    with pytest.raises(MarketDataUnavailableError):
        provider.load_range(date(2024, 1, 2), date(2024, 1, 3))


def test_alpaca_provider_duplicate_and_out_of_range_bars_are_fatal() -> None:
    duplicate_provider = _provider(
        lambda _: httpx.Response(
            200,
            json={
                "bars": [
                    {
                        "t": "2024-01-02T05:00:00Z",
                        "o": 470,
                        "h": 472,
                        "l": 469,
                        "c": 471,
                        "v": 1000,
                    },
                    {
                        "t": "2024-01-02T06:00:00Z",
                        "o": 470,
                        "h": 472,
                        "l": 469,
                        "c": 471,
                        "v": 1000,
                    },
                ]
            },
        )
    )
    with pytest.raises(MarketDataProviderError, match="duplicate"):
        duplicate_provider.load_range(date(2024, 1, 2), date(2024, 1, 3))

    out_of_range_provider = _provider(
        lambda _: httpx.Response(
            200,
            json={
                "bars": [
                    {
                        "t": "2024-01-04T05:00:00Z",
                        "o": 470,
                        "h": 472,
                        "l": 469,
                        "c": 471,
                        "v": 1000,
                    }
                ]
            },
        )
    )
    with pytest.raises(MarketDataProviderError, match="out-of-range"):
        out_of_range_provider.load_range(date(2024, 1, 2), date(2024, 1, 3))


@pytest.mark.parametrize("status_code", [401, 403, 429, 500])
def test_alpaca_provider_http_errors_raise_provider_error(status_code: int) -> None:
    provider = _provider(lambda _: httpx.Response(status_code, text="provider error"))

    with pytest.raises(MarketDataProviderError):
        provider.load_range(date(2024, 1, 2), date(2024, 1, 3))


def test_alpaca_provider_malformed_json_and_timeout_raise_provider_error() -> None:
    malformed = _provider(lambda _: httpx.Response(200, text="{"))
    with pytest.raises(MarketDataProviderError):
        malformed.load_range(date(2024, 1, 2), date(2024, 1, 3))

    def timeout_handler(_: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("forced timeout")

    with pytest.raises(MarketDataProviderError):
        _provider(timeout_handler).load_range(date(2024, 1, 2), date(2024, 1, 3))


def test_alpaca_provider_rejects_unsupported_symbol_and_frequency() -> None:
    provider = _provider(lambda _: httpx.Response(200, json={"bars": []}))

    with pytest.raises(MarketDataProviderError):
        provider.load_range(date(2024, 1, 2), date(2024, 1, 3), symbol="QQQ")
    with pytest.raises(MarketDataProviderError):
        provider.load_range(
            date(2024, 1, 2),
            date(2024, 1, 3),
            frequency=TradingFrequency.WEEKLY,
        )
