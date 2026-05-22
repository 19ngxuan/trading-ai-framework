from pydantic import Field

from app.api.schemas.experiment_schemas import CamelModel
from app.domain.enums import (
    AgentMode,
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    OrderStatus,
    StrategyType,
    TradingFrequency,
)


class OptionsResponse(CamelModel):
    assets: list[str]
    modes: list[ExperimentMode]
    strategies: list[StrategyType]
    experiment_statuses: list[ExperimentStatus] = Field(alias="experimentStatuses")
    trading_frequencies: list[TradingFrequency] = Field(alias="tradingFrequencies")
    fee_model_types: list[FeeModelType] = Field(alias="feeModelTypes")
    agent_modes: list[AgentMode] = Field(alias="agentModes")
    order_statuses: list[OrderStatus] = Field(alias="orderStatuses")
