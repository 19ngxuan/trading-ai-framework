import json
from decimal import Decimal

import httpx
import pytest

from app.domain.enums import OrderSide, OrderType
from app.modules.broker.alpaca_broker_adapter import AlpacaPaperTradingAdapter
from app.modules.broker.errors import BrokerProviderError


def _adapter(handler) -> AlpacaPaperTradingAdapter:
    return AlpacaPaperTradingAdapter(
        api_key_id="key",
        api_secret_key="secret",
        base_url="https://paper-api.alpaca.markets",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def _order_payload(**overrides) -> dict:
    payload = {
        "id": "alpaca-order-1",
        "status": "filled",
        "symbol": "SPY",
        "side": "buy",
        "qty": "10",
        "filled_qty": "10",
        "filled_avg_price": "100.50",
        "submitted_at": "2026-01-01T12:00:00Z",
        "filled_at": "2026-01-01T12:00:01Z",
    }
    payload.update(overrides)
    return payload


def test_place_order_uses_paper_endpoint_headers_and_payload() -> None:
    seen_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return httpx.Response(200, json=_order_payload())

    result = _adapter(handler).place_order(
        symbol="SPY",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.MARKET,
        client_order_id="experiment-1-step-2-risk-3",
    )

    assert seen_request is not None
    assert seen_request.method == "POST"
    assert seen_request.url.path == "/v2/orders"
    assert seen_request.headers["APCA-API-KEY-ID"] == "key"
    assert seen_request.headers["APCA-API-SECRET-KEY"] == "secret"
    request_json = json.loads(seen_request.content)
    assert request_json["client_order_id"] == "experiment-1-step-2-risk-3"
    assert request_json["symbol"] == "SPY"
    assert request_json["type"] == "market"
    assert request_json["time_in_force"] == "day"
    assert result.broker_order_id == "alpaca-order-1"
    assert result.status == "filled"
    assert result.filled_quantity == Decimal("10")
    assert result.average_fill_price == Decimal("100.50")


def test_get_order_status_maps_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v2/orders/alpaca-order-1"
        return httpx.Response(200, json=_order_payload(status="accepted"))

    result = _adapter(handler).get_order_status("alpaca-order-1")

    assert result.status == "accepted"
    assert result.symbol == "SPY"


@pytest.mark.parametrize("status_code", [401, 403, 429, 500])
def test_http_errors_raise_provider_error(status_code: int) -> None:
    adapter = _adapter(lambda _: httpx.Response(status_code, text="provider error"))

    with pytest.raises(BrokerProviderError):
        adapter.place_order(
            symbol="SPY",
            side=OrderSide.BUY,
            quantity=Decimal("1"),
            order_type=OrderType.MARKET,
            client_order_id="client-id",
        )


def test_malformed_json_and_timeout_raise_provider_error() -> None:
    malformed = _adapter(lambda _: httpx.Response(200, text="{"))
    with pytest.raises(BrokerProviderError):
        malformed.get_order_status("alpaca-order-1")

    def timeout_handler(_: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("forced timeout")

    with pytest.raises(BrokerProviderError):
        _adapter(timeout_handler).get_order_status("alpaca-order-1")


def test_unsupported_symbol_and_order_type_fail_before_http_call() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("unexpected HTTP call")

    adapter = _adapter(handler)

    with pytest.raises(BrokerProviderError):
        adapter.place_order(
            symbol="QQQ",
            side=OrderSide.BUY,
            quantity=Decimal("1"),
            order_type=OrderType.MARKET,
            client_order_id="client-id",
        )

    with pytest.raises(BrokerProviderError):
        adapter.place_order(
            symbol="SPY",
            side=OrderSide.BUY,
            quantity=Decimal("1"),
            order_type=object(),
            client_order_id="client-id",
        )
