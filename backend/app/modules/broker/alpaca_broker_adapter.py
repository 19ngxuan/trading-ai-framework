from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

import httpx

from app.domain.enums import OrderSide, OrderType
from app.domain.assets import is_supported_equity_symbol
from app.domain.assets import normalize_symbol
from app.modules.broker.broker_adapter import (
    BrokerAccountState,
    BrokerOrderResult,
    BrokerPosition,
)
from app.modules.broker.errors import BrokerConfigurationError, BrokerProviderError

PAPER_TRADING_BASE_URL = "https://paper-api.alpaca.markets"


class AlpacaPaperTradingAdapter:
    def __init__(
        self,
        *,
        api_key_id: str,
        api_secret_key: str,
        base_url: str = PAPER_TRADING_BASE_URL,
        timeout_seconds: int = 10,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key_id = api_key_id
        self.api_secret_key = api_secret_key
        _validate_paper_base_url(base_url)
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.client = client or httpx.Client(timeout=timeout_seconds)

    def place_order(
        self,
        *,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType,
        client_order_id: str,
    ) -> BrokerOrderResult:
        symbol = normalize_symbol(symbol)
        self._validate_order(symbol, order_type)
        response = self._request(
            "POST",
            "/v2/orders",
            json={
                "symbol": symbol,
                "qty": str(quantity),
                "side": side.value.lower(),
                "type": "market",
                "time_in_force": "day",
                "client_order_id": client_order_id,
            },
        )
        return self._map_order_response(self._json(response))

    def get_order_status(self, broker_order_id: str) -> BrokerOrderResult:
        response = self._request("GET", f"/v2/orders/{broker_order_id}")
        return self._map_order_response(self._json(response))

    def get_account_state(self) -> BrokerAccountState:
        payload = self._json(self._request("GET", "/v2/account"))
        return BrokerAccountState(
            cash=_optional_decimal(payload.get("cash")),
            status=payload.get("status"),
            raw=payload,
        )

    def get_positions(self) -> list[BrokerPosition]:
        payload = self._json(self._request("GET", "/v2/positions"))
        if not isinstance(payload, list):
            raise BrokerProviderError(
                "Alpaca positions response is malformed.",
                details={"payload": payload},
            )
        return [
            BrokerPosition(
                symbol=str(item.get("symbol")),
                quantity=Decimal(str(item.get("qty", "0"))),
                market_value=_optional_decimal(item.get("market_value")),
                raw=item,
            )
            for item in payload
            if isinstance(item, dict)
        ]

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        try:
            response = self.client.request(
                method,
                f"{self.base_url}{path}",
                headers={
                    "APCA-API-KEY-ID": self.api_key_id,
                    "APCA-API-SECRET-KEY": self.api_secret_key,
                },
                json=json,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            raise BrokerProviderError(
                "Alpaca paper trading request failed.",
                details={
                    "statusCode": exc.response.status_code,
                    "responseText": exc.response.text,
                },
            ) from exc
        except httpx.HTTPError as exc:
            raise BrokerProviderError(
                "Alpaca paper trading request failed.",
                details={"error": str(exc)},
            ) from exc

    def _json(self, response: httpx.Response) -> dict | list:
        try:
            payload = response.json()
        except ValueError as exc:
            raise BrokerProviderError(
                "Alpaca paper trading response was not valid JSON.",
                details={"responseText": response.text},
            ) from exc
        if not isinstance(payload, dict | list):
            raise BrokerProviderError(
                "Alpaca paper trading response is malformed.",
                details={"payload": payload},
            )
        return payload

    def _map_order_response(self, payload: dict | list) -> BrokerOrderResult:
        if not isinstance(payload, dict):
            raise BrokerProviderError(
                "Alpaca order response is malformed.",
                details={"payload": payload},
            )
        try:
            return BrokerOrderResult(
                broker_order_id=str(payload["id"]),
                status=str(payload["status"]),
                symbol=str(payload["symbol"]),
                side=OrderSide(str(payload["side"]).upper()),
                quantity=Decimal(str(payload["qty"])),
                filled_quantity=Decimal(str(payload.get("filled_qty") or "0")),
                average_fill_price=_optional_decimal(payload.get("filled_avg_price")),
                submitted_at=_parse_datetime(payload.get("submitted_at")),
                filled_at=_parse_datetime(payload.get("filled_at")),
                raw=payload,
                error_message=payload.get("reject_reason"),
            )
        except (KeyError, ValueError, InvalidOperation) as exc:
            raise BrokerProviderError(
                "Alpaca order response is malformed.",
                details={"payload": payload, "error": str(exc)},
            ) from exc

    def _validate_order(self, symbol: str, order_type: OrderType) -> None:
        if not is_supported_equity_symbol(symbol):
            raise BrokerProviderError(
                "Alpaca paper trading adapter supports configured equity symbols only.",
                details={"symbol": symbol},
            )
        if order_type is not OrderType.MARKET:
            raise BrokerProviderError(
                "Alpaca paper trading adapter supports market orders only.",
                details={"orderType": getattr(order_type, "value", str(order_type))},
            )


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(
        tzinfo=None
    )


def _validate_paper_base_url(base_url: str) -> None:
    parsed = urlparse(base_url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "paper-api.alpaca.markets"
        or parsed.path.rstrip("/")
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise BrokerConfigurationError(
            "Alpaca paper trading adapter only accepts the paper trading base URL.",
            details={"baseUrl": base_url, "expectedBaseUrl": PAPER_TRADING_BASE_URL},
        )
