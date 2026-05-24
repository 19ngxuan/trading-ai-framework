from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.domain.enums import (
    AgentMode,
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    StrategyType,
    TradingFrequency,
)
from app.api.schemas.metrics_schemas import MetricSnapshotResponse, TradeSummaryResponse


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


class StrategyConfigInput(CamelModel):
    strategy_version: str = Field(alias="strategyVersion")
    moving_average_window: int | None = Field(default=None, alias="movingAverageWindow")
    position_sizing_type: str | None = Field(default=None, alias="positionSizingType")
    position_sizing_value: Decimal | None = Field(
        default=None, alias="positionSizingValue"
    )
    agent_mode: AgentMode | None = Field(default=None, alias="agentMode")
    model_name: str | None = Field(default=None, alias="modelName")
    confidence_threshold: Decimal | None = Field(default=None, alias="confidenceThreshold")
    parameters_json: dict[str, Any] | None = Field(default=None, alias="parametersJson")


class CreateExperimentRequest(CamelModel):
    name: str
    mode: ExperimentMode
    strategy_type: StrategyType = Field(alias="strategyType")
    asset_symbol: str = Field(alias="assetSymbol")
    initial_capital: Decimal = Field(alias="initialCapital")
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    trading_frequency: TradingFrequency = Field(alias="tradingFrequency")
    fee_model_type: FeeModelType = Field(alias="feeModelType")
    fee_value: Decimal = Field(alias="feeValue")
    strategy_config: StrategyConfigInput = Field(alias="strategyConfig")


class ExperimentResponse(CamelModel):
    id: int
    name: str
    mode: ExperimentMode
    strategy_type: StrategyType = Field(alias="strategyType")
    asset_symbol: str = Field(alias="assetSymbol")
    status: ExperimentStatus
    initial_capital: Decimal = Field(alias="initialCapital")
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    trading_frequency: TradingFrequency = Field(alias="tradingFrequency")
    fee_model_type: FeeModelType = Field(alias="feeModelType")
    fee_value: Decimal = Field(alias="feeValue")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class StrategyConfigResponse(StrategyConfigInput):
    id: int
    experiment_id: int = Field(alias="experimentId")
    strategy_type: StrategyType = Field(alias="strategyType")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class PortfolioResponse(CamelModel):
    id: int
    experiment_id: int = Field(alias="experimentId")
    cash: Decimal
    position_symbol: str | None = Field(alias="positionSymbol")
    position_quantity: Decimal | None = Field(alias="positionQuantity")
    current_price: Decimal | None = Field(alias="currentPrice")
    current_position_value: Decimal | None = Field(alias="currentPositionValue")
    current_portfolio_value: Decimal | None = Field(alias="currentPortfolioValue")
    updated_at: datetime = Field(alias="updatedAt")


class CreateExperimentResponse(CamelModel):
    experiment: ExperimentResponse
    portfolio: PortfolioResponse


class ExperimentSummaryResponse(CamelModel):
    id: int
    name: str
    mode: ExperimentMode
    strategy_type: StrategyType = Field(alias="strategyType")
    asset_symbol: str = Field(alias="assetSymbol")
    status: ExperimentStatus
    current_portfolio_value: Decimal | None = Field(alias="currentPortfolioValue")
    total_return: Decimal | None = Field(alias="totalReturn")
    profit_loss: Decimal | None = Field(alias="profitLoss")
    number_of_trades: int | None = Field(alias="numberOfTrades")
    max_drawdown: Decimal | None = Field(alias="maxDrawdown")
    last_trade: TradeSummaryResponse | None = Field(alias="lastTrade")
    latest_agent_decisions: list[dict[str, Any]] = Field(alias="latestAgentDecisions")


class PaginatedExperimentSummaryResponse(CamelModel):
    items: list[ExperimentSummaryResponse]
    limit: int
    offset: int
    total: int


class ExperimentDetailResponse(CamelModel):
    experiment: ExperimentResponse
    strategy_config: StrategyConfigResponse = Field(alias="strategyConfig")
    portfolio: PortfolioResponse
    latest_metrics: MetricSnapshotResponse | None = Field(alias="latestMetrics")
    latest_agent_decisions: list[dict[str, Any]] = Field(alias="latestAgentDecisions")


class ExperimentActionResponse(CamelModel):
    experiment_id: int = Field(alias="experimentId")
    status: ExperimentStatus
    message: str | None = None
