from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.domain.enums import OrderSide


class CamelModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_decimal(self, value):
        if isinstance(value, Decimal):
            return float(value)
        return value


class TradeSummaryResponse(CamelModel):
    side: OrderSide
    quantity: Decimal
    price: Decimal
    timestamp: datetime


class MetricSnapshotResponse(CamelModel):
    timestamp: datetime
    total_return: Decimal | None = Field(alias="totalReturn")
    profit_loss: Decimal | None = Field(alias="profitLoss")
    number_of_trades: int | None = Field(alias="numberOfTrades")
    max_drawdown: Decimal | None = Field(alias="maxDrawdown")
    buy_and_hold_return: Decimal | None = Field(alias="buyAndHoldReturn")
    difference_to_buy_and_hold: Decimal | None = Field(alias="differenceToBuyAndHold")


class PortfolioSnapshotResponse(CamelModel):
    timestamp: datetime
    cash: Decimal
    position_symbol: str | None = Field(alias="positionSymbol")
    position_quantity: Decimal | None = Field(alias="positionQuantity")
    position_market_value: Decimal | None = Field(alias="positionMarketValue")
    total_portfolio_value: Decimal | None = Field(alias="totalPortfolioValue")
    current_price: Decimal | None = Field(alias="currentPrice")


class PaginatedMetricSnapshotResponse(CamelModel):
    items: list[MetricSnapshotResponse]
    limit: int
    offset: int
    total: int


class PaginatedPortfolioSnapshotResponse(CamelModel):
    items: list[PortfolioSnapshotResponse]
    limit: int
    offset: int
    total: int
