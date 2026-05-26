from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.domain.enums import OrderSide


class CamelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_decimal(self, value):
        if isinstance(value, Decimal):
            return float(value)
        return value


class TradeResponse(CamelModel):
    id: int
    execution_step_id: int = Field(alias="executionStepId")
    experiment_id: int = Field(alias="experimentId")
    order_id: int = Field(alias="orderId")
    timestamp: datetime
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    order_value: Decimal | None = Field(alias="orderValue")
    fee: Decimal | None
    portfolio_value_after_trade: Decimal | None = Field(alias="portfolioValueAfterTrade")
    created_at: datetime = Field(alias="createdAt")


class PaginatedTradeResponse(CamelModel):
    items: list[TradeResponse]
    limit: int
    offset: int
    total: int
