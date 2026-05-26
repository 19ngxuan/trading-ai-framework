from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    ExecutionStepStatus,
    ExperimentMode,
    ExperimentStatus,
    StrategyType,
    TradingFrequency,
    TriggerType,
)


class CamelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PaperExecutionStepSummary(CamelModel):
    id: int
    status: ExecutionStepStatus
    trigger_type: TriggerType = Field(alias="triggerType")
    sequence_number: int = Field(alias="sequenceNumber")
    scheduled_for: datetime | None = Field(alias="scheduledFor")
    started_at: datetime | None = Field(alias="startedAt")
    completed_at: datetime | None = Field(alias="completedAt")
    error_message: str | None = Field(alias="errorMessage")
    created_at: datetime = Field(alias="createdAt")


class PaperStatusResponse(CamelModel):
    experiment_id: int = Field(alias="experimentId")
    experiment_status: ExperimentStatus = Field(alias="experimentStatus")
    mode: ExperimentMode
    strategy_type: StrategyType = Field(alias="strategyType")
    trading_frequency: TradingFrequency = Field(alias="tradingFrequency")
    asset_symbol: str = Field(alias="assetSymbol")
    supported_by_paper_scheduler: bool = Field(alias="supportedByPaperScheduler")
    paper_trading_scheduler_enabled: bool = Field(alias="paperTradingSchedulerEnabled")
    alpaca_paper_trading_enabled: bool = Field(alias="alpacaPaperTradingEnabled")
    daily_evaluation_time: str = Field(alias="dailyEvaluationTime")
    timezone: str
    current_due_slot: datetime | None = Field(alias="currentDueSlot")
    next_eligible_evaluation_time: datetime | None = Field(
        alias="nextEligibleEvaluationTime"
    )
    already_executed_current_due_slot: bool = Field(
        alias="alreadyExecutedCurrentDueSlot"
    )
    open_submitted_orders_count: int = Field(alias="openSubmittedOrdersCount")
    last_broker_sync_timestamp: datetime | None = Field(alias="lastBrokerSyncTimestamp")
    last_paper_execution_step: PaperExecutionStepSummary | None = Field(
        alias="lastPaperExecutionStep"
    )
    reason_code: str = Field(alias="reasonCode")
    message: str
    operational_metadata: dict | None = Field(default=None, alias="operationalMetadata")
