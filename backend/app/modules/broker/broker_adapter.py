from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from app.domain.enums import OrderSide, OrderType


@dataclass(frozen=True)
class BrokerOrderResult:
    broker_order_id: str
    status: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    filled_quantity: Decimal
    average_fill_price: Decimal | None
    submitted_at: datetime | None
    filled_at: datetime | None
    raw: dict
    error_message: str | None = None


@dataclass(frozen=True)
class BrokerAccountState:
    cash: Decimal | None
    status: str | None
    raw: dict


@dataclass(frozen=True)
class BrokerPosition:
    symbol: str
    quantity: Decimal
    market_value: Decimal | None
    raw: dict


class BrokerAdapter(Protocol):
    def place_order(
        self,
        *,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType,
        client_order_id: str,
    ) -> BrokerOrderResult:
        ...

    def get_order_status(self, broker_order_id: str) -> BrokerOrderResult:
        ...

    def get_account_state(self) -> BrokerAccountState:
        ...

    def get_positions(self) -> list[BrokerPosition]:
        ...
