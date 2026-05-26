from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.domain.enums import BrokerName, OrderMode, OrderSide, OrderStatus, OrderType


class CamelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_decimal(self, value):
        if isinstance(value, Decimal):
            return float(value)
        return value


class OrderResponse(CamelModel):
    id: int
    execution_step_id: int = Field(alias="executionStepId")
    experiment_id: int = Field(alias="experimentId")
    risk_check_id: int = Field(alias="riskCheckId")
    mode: OrderMode
    broker_name: BrokerName | None = Field(alias="brokerName")
    broker_order_id: str | None = Field(alias="brokerOrderId")
    symbol: str
    side: OrderSide
    quantity: Decimal
    order_type: OrderType = Field(alias="orderType")
    status: OrderStatus
    submitted_at: datetime | None = Field(alias="submittedAt")
    filled_at: datetime | None = Field(alias="filledAt")
    average_fill_price: Decimal | None = Field(alias="averageFillPrice")
    error_message: str | None = Field(alias="errorMessage")
    created_at: datetime = Field(alias="createdAt")


class PaginatedOrderResponse(CamelModel):
    items: list[OrderResponse]
    limit: int
    offset: int
    total: int
