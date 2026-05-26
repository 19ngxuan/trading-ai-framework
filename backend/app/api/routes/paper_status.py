from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.paper_status_schemas import (
    PaperExecutionStepSummary,
    PaperStatusResponse,
)
from app.core.config import Settings, get_settings
from app.core.errors import NotFoundAppError
from app.domain.enums import (
    ExperimentMode,
    ExperimentStatus,
    StrategyType,
    TradingFrequency,
)
from app.modules.market_data.trading_calendar import UsEquitiesTradingCalendar
from app.modules.scheduler.jobs import _paper_daily_due_slot, _paper_smoke_test_due_slot
from app.persistence.database import get_session
from app.persistence.models import ExperimentModel
from app.persistence.repositories import (
    BrokerSyncLogRepository,
    ExecutionStepRepository,
    ExperimentRepository,
    OrderRepository,
)

router = APIRouter(prefix="/experiments", tags=["paper-status"])
NEW_YORK_TZ = ZoneInfo("America/New_York")


@router.get("/{experiment_id}/paper-status", response_model=PaperStatusResponse)
def get_experiment_paper_status(
    experiment_id: int,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PaperStatusResponse:
    experiment = ExperimentRepository(session).get_by_id(experiment_id)
    if experiment is None:
        raise NotFoundAppError(
            "Experiment was not found.",
            details={"experimentId": experiment_id},
        )

    execution_steps = ExecutionStepRepository(session)
    orders = OrderRepository(session)
    broker_sync_logs = BrokerSyncLogRepository(session)
    now = datetime.now(NEW_YORK_TZ)
    is_smoke_test = experiment.strategy_type is StrategyType.PAPER_TRADING_SMOKE_TEST
    current_due_slot = (
        _paper_smoke_test_due_slot(now=now)
        if is_smoke_test and settings.paper_trading_test_mode_enabled
        else _paper_daily_due_slot(
            now=now,
            daily_evaluation_time=settings.paper_trading_daily_evaluation_time,
        )
    )
    next_evaluation_time = _next_evaluation_time(
        now=now,
        daily_evaluation_time=settings.paper_trading_daily_evaluation_time,
        smoke_test=is_smoke_test and settings.paper_trading_test_mode_enabled,
    )
    open_order_count = orders.count_open_submitted_by_experiment(experiment_id)
    last_sync = broker_sync_logs.latest_by_experiment(experiment_id)
    last_step = execution_steps.latest_by_experiment(experiment_id)
    already_executed = (
        current_due_slot is not None
        and execution_steps.has_step_for_scheduled_slot(experiment_id, current_due_slot)
    )
    supported = _supported_by_paper_scheduler(experiment)
    reason_code, message = _status_reason(
        experiment=experiment,
        supported=supported,
        settings=settings,
        current_due_slot=current_due_slot,
        already_executed=already_executed,
        open_order_count=open_order_count,
        local_date=now.date(),
    )

    return PaperStatusResponse(
        experimentId=experiment.id,
        experimentStatus=experiment.status,
        mode=experiment.mode,
        strategyType=experiment.strategy_type,
        tradingFrequency=experiment.trading_frequency,
        assetSymbol=experiment.asset_symbol,
        supportedByPaperScheduler=supported,
        paperTradingSchedulerEnabled=settings.paper_trading_scheduler_enabled,
        alpacaPaperTradingEnabled=settings.alpaca_paper_trading_enabled,
        dailyEvaluationTime=settings.paper_trading_daily_evaluation_time,
        timezone="America/New_York",
        currentDueSlot=current_due_slot,
        nextEligibleEvaluationTime=next_evaluation_time,
        alreadyExecutedCurrentDueSlot=already_executed,
        openSubmittedOrdersCount=open_order_count,
        lastBrokerSyncTimestamp=last_sync.timestamp if last_sync is not None else None,
        lastPaperExecutionStep=(
            PaperExecutionStepSummary.model_validate(last_step)
            if last_step is not None
            else None
        ),
        reasonCode=reason_code,
        message=message,
    )


def _supported_by_paper_scheduler(experiment: ExperimentModel) -> bool:
    if (
        experiment.mode is ExperimentMode.PAPER_TRADING
        and experiment.strategy_type is StrategyType.BUY_AND_HOLD
        and experiment.trading_frequency is TradingFrequency.DAILY
        and experiment.asset_symbol == "SPY"
    ):
        return True
    return (
        experiment.mode is ExperimentMode.PAPER_TRADING
        and experiment.strategy_type is StrategyType.PAPER_TRADING_SMOKE_TEST
        and experiment.trading_frequency is TradingFrequency.TEST_1_MIN
        and experiment.asset_symbol == "SPY"
    )


def _status_reason(
    *,
    experiment: ExperimentModel,
    supported: bool,
    settings: Settings,
    current_due_slot: datetime | None,
    already_executed: bool,
    open_order_count: int,
    local_date: date,
) -> tuple[str, str]:
    if experiment.mode is not ExperimentMode.PAPER_TRADING:
        return "NOT_PAPER_TRADING", "This experiment is not a paper trading experiment."
    if (
        experiment.strategy_type is StrategyType.PAPER_TRADING_SMOKE_TEST
        and not settings.paper_trading_test_mode_enabled
    ):
        return (
            "PAPER_TRADING_TEST_MODE_DISABLED",
            "Paper trading smoke-test mode is disabled, so no smoke-test steps will be scheduled.",
        )
    if not supported:
        return (
            "UNSUPPORTED_PAPER_CONFIGURATION",
            "The paper scheduler supports PAPER_TRADING + BUY_AND_HOLD + DAILY + SPY "
            "and gated PAPER_TRADING_SMOKE_TEST + TEST_1_MIN + SPY.",
        )
    if not settings.paper_trading_scheduler_enabled:
        return (
            "PAPER_TRADING_SCHEDULER_DISABLED",
            "Paper trading scheduler is disabled. Start changes lifecycle only and will not submit an order until scheduled execution is enabled.",
        )
    if not settings.alpaca_paper_trading_enabled:
        return (
            "ALPACA_PAPER_TRADING_DISABLED",
            "Alpaca paper trading is disabled, so scheduled paper execution cannot submit orders.",
        )
    if experiment.status is not ExperimentStatus.RUNNING:
        return (
            "EXPERIMENT_NOT_RUNNING",
            "The experiment is not RUNNING, so no new scheduled paper steps will be created.",
        )
    if open_order_count > 0:
        return (
            "OPEN_ORDER_PENDING_SYNC",
            "There is at least one submitted paper order waiting for broker sync.",
        )
    if current_due_slot is None:
        if experiment.strategy_type is StrategyType.PAPER_TRADING_SMOKE_TEST:
            if _is_trading_day(local_date):
                return (
                    "WAITING_FOR_REGULAR_MARKET_HOURS",
                    "The smoke-test strategy runs only during US regular market hours.",
                )
            return (
                "NON_TRADING_DAY",
                "Today is not a US equities trading day, so no smoke-test step is due.",
            )
        if _is_trading_day(local_date):
            return (
                "WAITING_FOR_DAILY_EVALUATION_TIME",
                "The experiment is waiting for the configured daily paper evaluation time.",
            )
        return (
            "NON_TRADING_DAY",
            "Today is not a US equities trading day, so no paper step is due.",
        )
    if already_executed:
        if experiment.strategy_type is StrategyType.PAPER_TRADING_SMOKE_TEST:
            return (
                "CURRENT_TEST_SLOT_ALREADY_EXECUTED",
                "The current smoke-test minute slot has already been executed.",
            )
        return (
            "CURRENT_DUE_SLOT_ALREADY_EXECUTED",
            "The current daily paper evaluation slot has already been executed.",
        )
    return (
        "READY_FOR_NEXT_SCHEDULED_EVALUATION",
        "The experiment is eligible for the next scheduled paper evaluation.",
    )


def _next_evaluation_time(
    *, now: datetime, daily_evaluation_time: str, smoke_test: bool
) -> datetime | None:
    local_now = now.astimezone(NEW_YORK_TZ)
    if smoke_test:
        current_slot = _paper_smoke_test_due_slot(now=local_now)
        if current_slot is not None:
            return current_slot
        calendar = UsEquitiesTradingCalendar()
        for day_offset in range(0, 15):
            candidate_date = local_now.date() + timedelta(days=day_offset)
            sessions = calendar.sessions_between(candidate_date, candidate_date)
            if not sessions:
                continue
            session = sessions[0]
            candidate = datetime.combine(
                candidate_date,
                session.open_time,
                tzinfo=NEW_YORK_TZ,
            )
            if candidate >= local_now:
                return candidate.astimezone(UTC).replace(tzinfo=None)
        return None

    hour, minute = _parse_hh_mm(daily_evaluation_time)
    calendar = UsEquitiesTradingCalendar()
    for day_offset in range(0, 15):
        candidate_date = local_now.date() + timedelta(days=day_offset)
        if not calendar.sessions_between(candidate_date, candidate_date):
            continue
        candidate = datetime.combine(
            candidate_date,
            time(hour=hour, minute=minute),
            tzinfo=NEW_YORK_TZ,
        )
        if candidate >= local_now:
            return candidate.astimezone(UTC).replace(tzinfo=None)
    return None


def _is_trading_day(value: date) -> bool:
    return bool(UsEquitiesTradingCalendar().sessions_between(value, value))


def _parse_hh_mm(value: str) -> tuple[int, int]:
    hour, minute = value.split(":")
    return int(hour), int(minute)
