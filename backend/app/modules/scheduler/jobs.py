import logging
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import ExperimentStepAlreadyRunningAppError
from app.domain.enums import TriggerType
from app.modules.execution.broker_sync import BrokerSyncRunResult, PaperBrokerSyncService
from app.modules.execution.paper_step_runner import PaperTradingStepRunner
from app.modules.execution.step_runner import HistoricalStepRunner, StepRunResult
from app.modules.events.service import EventScannerService
from app.modules.market_data.errors import MarketDataProviderError, MarketDataUnavailableError
from app.modules.market_data.factory import create_intraday_market_data_provider
from app.modules.market_data.hourly_bars import latest_completed_hourly_window
from app.modules.market_data.intraday_provider import IntradayMarketDataProvider
from app.modules.market_data.trading_calendar import (
    TradingSession,
    UsEquitiesTradingCalendar,
)
from app.persistence.database import create_session_factory
from app.persistence.repositories import ExperimentRepository

logger = logging.getLogger(__name__)
NEW_YORK_TZ = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class ScheduledStepSkip:
    experiment_id: int
    error_code: str
    message: str


@dataclass(frozen=True)
class ScheduledStepError:
    experiment_id: int
    error_type: str
    message: str


@dataclass(frozen=True)
class SchedulerTickResult:
    results: list[StepRunResult]
    skipped: list[ScheduledStepSkip]
    errors: list[ScheduledStepError]


@dataclass(frozen=True)
class PaperSchedulerTickResult:
    results: list[StepRunResult]
    skipped: list[ScheduledStepSkip]
    errors: list[ScheduledStepError]
    due_slot: datetime | None


def trigger_due_experiments(
    *,
    session_factory: sessionmaker[Session] | None = None,
    step_runner: HistoricalStepRunner | None = None,
) -> SchedulerTickResult:
    session_factory = session_factory or create_session_factory()
    step_runner = step_runner or HistoricalStepRunner(session_factory=session_factory)
    with session_factory() as session:
        experiment_ids = ExperimentRepository(
            session
        ).list_scheduler_eligible_experiment_ids()

    results: list[StepRunResult] = []
    skipped: list[ScheduledStepSkip] = []
    errors: list[ScheduledStepError] = []
    for experiment_id in experiment_ids:
        try:
            results.append(
                step_runner.run_next_step(
                    experiment_id,
                    trigger_type=TriggerType.SCHEDULED,
                )
            )
        except ExperimentStepAlreadyRunningAppError as exc:
            logger.info(
                "Skipping scheduled step for experiment %s: %s",
                experiment_id,
                exc.message,
            )
            skipped.append(
                ScheduledStepSkip(
                    experiment_id=experiment_id,
                    error_code=exc.error_code,
                    message=exc.message,
                )
            )
        except Exception as exc:
            logger.exception(
                "Scheduled step failed for experiment %s.",
                experiment_id,
            )
            errors.append(
                ScheduledStepError(
                    experiment_id=experiment_id,
                    error_type=type(exc).__name__,
                    message=str(exc),
                )
            )
    return SchedulerTickResult(results=results, skipped=skipped, errors=errors)


def trigger_due_paper_trading_experiments(
    *,
    session_factory: sessionmaker[Session] | None = None,
    step_runner: PaperTradingStepRunner | None = None,
    now: datetime | None = None,
    daily_evaluation_time: str = "15:55",
    paper_trading_test_mode_enabled: bool = False,
    intraday_provider: IntradayMarketDataProvider | None = None,
) -> PaperSchedulerTickResult:
    daily_due_slot = _paper_daily_due_slot(
        now=now or datetime.now(NEW_YORK_TZ),
        daily_evaluation_time=daily_evaluation_time,
    )
    local_now = now or datetime.now(NEW_YORK_TZ)
    smoke_test_due_slot = (
        _paper_smoke_test_due_slot(now=local_now)
        if paper_trading_test_mode_enabled
        else None
    )
    hourly_due_slot = _paper_hourly_due_slot(now=local_now)
    orb_due_slot = _paper_orb_due_slot(now=local_now)
    if (
        daily_due_slot is None
        and smoke_test_due_slot is None
        and hourly_due_slot is None
        and orb_due_slot is None
    ):
        return PaperSchedulerTickResult(
            results=[],
            skipped=[],
            errors=[],
            due_slot=None,
        )

    session_factory = session_factory or create_session_factory()
    step_runner = step_runner or PaperTradingStepRunner(session_factory=session_factory)
    pre_errors: list[ScheduledStepError] = []
    with session_factory() as session:
        repository = ExperimentRepository(session)
        scheduled_experiments: list[
            tuple[int, datetime | None, str | None, str | None]
        ] = []
        reported_due_slot: datetime | None = None
        if daily_due_slot is not None:
            daily_ids = repository.list_paper_daily_scheduler_eligible_experiment_ids()
            if daily_ids:
                reported_due_slot = reported_due_slot or daily_due_slot
            scheduled_experiments.extend(
                (experiment_id, daily_due_slot, None, None)
                for experiment_id in daily_ids
            )
        provider = None
        if hourly_due_slot is not None:
            hourly_ids = repository.list_paper_hourly_ai_scheduler_eligible_experiment_ids()
            if hourly_ids:
                reported_due_slot = reported_due_slot or hourly_due_slot
            scheduled_experiments.extend(
                (experiment_id, hourly_due_slot, None, None)
                for experiment_id in hourly_ids
            )
        if smoke_test_due_slot is not None:
            smoke_ids = repository.list_paper_smoke_test_scheduler_eligible_experiment_ids()
            if smoke_ids:
                reported_due_slot = reported_due_slot or smoke_test_due_slot
            scheduled_experiments.extend(
                (experiment_id, smoke_test_due_slot, None, None)
                for experiment_id in smoke_ids
            )
        if orb_due_slot is not None:
            orb_ids = repository.list_paper_orb_scheduler_eligible_experiment_ids()
            if orb_ids:
                reported_due_slot = reported_due_slot or orb_due_slot
                provider = provider or intraday_provider or create_intraday_market_data_provider(
                    step_runner.settings
                )
            for experiment_id in orb_ids:
                experiment = repository.get_by_id(experiment_id)
                if experiment is None:
                    continue
                try:
                    provider.load_session_until(
                        orb_due_slot.date(),
                        orb_due_slot,
                        symbol=experiment.asset_symbol,
                    )
                except MarketDataUnavailableError as exc:
                    logger.info(
                        "Skipping ORB paper step for experiment %s: %s",
                        experiment_id,
                        exc.message,
                    )
                    # Keep missing completed bars as a scheduler skip with no step.
                    scheduled_experiments.append(
                        (
                            experiment_id,
                            None,
                            "PAPER_ORB_COMPLETED_BAR_UNAVAILABLE",
                            "Expected completed ORB bar is not available yet.",
                        )
                    )
                except MarketDataProviderError as exc:
                    logger.exception(
                        "ORB paper market-data preflight failed for experiment %s.",
                        experiment_id,
                    )
                    pre_errors.append(
                        ScheduledStepError(
                            experiment_id=experiment_id,
                            error_type=type(exc).__name__,
                            message=exc.message,
                        )
                    )
                else:
                    scheduled_experiments.append(
                        (experiment_id, orb_due_slot, None, None)
                    )

    results: list[StepRunResult] = []
    skipped: list[ScheduledStepSkip] = []
    errors: list[ScheduledStepError] = pre_errors
    for experiment_id, due_slot, skip_code, skip_message in scheduled_experiments:
        if due_slot is None:
            skipped.append(
                ScheduledStepSkip(
                    experiment_id=experiment_id,
                    error_code=skip_code or "PAPER_STEP_UNAVAILABLE",
                    message=skip_message or "Expected paper trading slot is not available.",
                )
            )
            continue
        try:
            results.append(
                step_runner.run_next_step(
                    experiment_id,
                    trigger_type=TriggerType.SCHEDULED,
                    scheduled_for=due_slot,
                )
            )
        except ExperimentStepAlreadyRunningAppError as exc:
            logger.info(
                "Skipping scheduled paper step for experiment %s: %s",
                experiment_id,
                exc.message,
            )
            skipped.append(
                ScheduledStepSkip(
                    experiment_id=experiment_id,
                    error_code=exc.error_code,
                    message=exc.message,
                )
            )
        except Exception as exc:
            logger.exception(
                "Scheduled paper step failed for experiment %s.",
                experiment_id,
            )
            errors.append(
                ScheduledStepError(
                    experiment_id=experiment_id,
                    error_type=type(exc).__name__,
                    message=str(exc),
                )
            )
    return PaperSchedulerTickResult(
        results=results,
        skipped=skipped,
        errors=errors,
        due_slot=reported_due_slot,
    )


def sync_open_paper_broker_orders(
    *,
    sync_service: PaperBrokerSyncService | None = None,
) -> BrokerSyncRunResult:
    sync_service = sync_service or PaperBrokerSyncService()
    return sync_service.sync_open_orders()


def scan_news_events_and_trigger_agent_runs(
    *,
    event_service: EventScannerService | None = None,
) -> dict:
    event_service = event_service or EventScannerService()
    return event_service.scan_once()


def _paper_daily_due_slot(
    *, now: datetime, daily_evaluation_time: str
) -> datetime | None:
    if now.tzinfo is None:
        now = now.replace(tzinfo=NEW_YORK_TZ)
    local_now = now.astimezone(NEW_YORK_TZ)
    sessions = UsEquitiesTradingCalendar().sessions_between(
        local_now.date(),
        local_now.date(),
    )
    if not sessions:
        return None
    hour, minute = _parse_hh_mm(daily_evaluation_time)
    due_local = datetime.combine(
        local_now.date(),
        time(hour=hour, minute=minute),
        tzinfo=NEW_YORK_TZ,
    )
    if local_now < due_local:
        return None
    return due_local.astimezone(UTC).replace(tzinfo=None)


def _paper_smoke_test_due_slot(*, now: datetime) -> datetime | None:
    if now.tzinfo is None:
        now = now.replace(tzinfo=NEW_YORK_TZ)
    local_now = now.astimezone(NEW_YORK_TZ)
    sessions = UsEquitiesTradingCalendar().sessions_between(
        local_now.date(),
        local_now.date(),
    )
    if not sessions:
        return None
    session = sessions[0]
    open_time = datetime.combine(local_now.date(), session.open_time, tzinfo=NEW_YORK_TZ)
    close_time = datetime.combine(
        local_now.date(), session.close_time, tzinfo=NEW_YORK_TZ
    )
    if local_now < open_time or local_now >= close_time:
        return None
    due_local = local_now.replace(second=0, microsecond=0)
    return due_local.astimezone(UTC).replace(tzinfo=None)


def _paper_orb_due_slot(*, now: datetime) -> datetime | None:
    if now.tzinfo is None:
        now = now.replace(tzinfo=NEW_YORK_TZ)
    local_now = now.astimezone(NEW_YORK_TZ)
    sessions = UsEquitiesTradingCalendar().sessions_between(
        local_now.date(),
        local_now.date(),
    )
    if not sessions:
        return None
    session = sessions[0]
    due_local = _latest_completed_bar_start(local_now, session)
    if due_local is None:
        return None
    return due_local.replace(tzinfo=None)


def _paper_hourly_due_slot(*, now: datetime) -> datetime | None:
    if now.tzinfo is None:
        now = now.replace(tzinfo=NEW_YORK_TZ)
    local_now = now.astimezone(NEW_YORK_TZ)
    sessions = UsEquitiesTradingCalendar().sessions_between(
        local_now.date(),
        local_now.date(),
    )
    if not sessions:
        return None
    window = latest_completed_hourly_window(local_now, sessions[0])
    if window is None:
        return None
    return window.start.replace(tzinfo=NEW_YORK_TZ).astimezone(UTC).replace(
        tzinfo=None
    )


def _latest_completed_bar_start(
    local_now: datetime,
    session: TradingSession,
) -> datetime | None:
    expected = [
        datetime.combine(session.session_date, timestamp.time(), tzinfo=NEW_YORK_TZ)
        for timestamp in session.expected_bar_start_times
    ]
    completed = [timestamp for timestamp in expected if timestamp + timedelta(minutes=5) <= local_now]
    if not completed:
        return None
    return completed[-1]


def _parse_hh_mm(value: str) -> tuple[int, int]:
    hour, minute = value.split(":")
    return int(hour), int(minute)
