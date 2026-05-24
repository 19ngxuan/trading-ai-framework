from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.domain.enums import ExperimentMode, ExperimentStatus, StrategyType


class CamelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_decimal(self, value):
        if isinstance(value, Decimal):
            return float(value)
        return value


class CompareExperimentsRequest(CamelModel):
    experiment_ids: list[int] = Field(alias="experimentIds")
    benchmark_experiment_id: int | None = Field(
        default=None, alias="benchmarkExperimentId"
    )


class CompareExperimentRow(CamelModel):
    experiment_id: int = Field(alias="experimentId")
    name: str
    mode: ExperimentMode
    strategy_type: StrategyType = Field(alias="strategyType")
    status: ExperimentStatus
    asset_symbol: str = Field(alias="assetSymbol")
    latest_portfolio_value: Decimal | None = Field(alias="latestPortfolioValue")
    total_return: Decimal | None = Field(alias="totalReturn")
    profit_loss: Decimal | None = Field(alias="profitLoss")
    number_of_trades: int | None = Field(alias="numberOfTrades")
    max_drawdown: Decimal | None = Field(alias="maxDrawdown")
    benchmark_return: Decimal | None = Field(alias="benchmarkReturn")
    difference_to_benchmark: Decimal | None = Field(alias="differenceToBenchmark")


class CompareExperimentsResponse(CamelModel):
    benchmark_experiment_id: int | None = Field(alias="benchmarkExperimentId")
    items: list[CompareExperimentRow]
