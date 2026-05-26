import logging
from dataclasses import dataclass
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import ExperimentStepAlreadyRunningAppError
from app.domain.enums import TriggerType
from app.modules.execution.broker_sync import BrokerSyncRunResult, PaperBrokerSyncService
from app.modules.execution.paper_step_runner import PaperTradingStepRunner
from app.modules.execution.step_runner import HistoricalStepRunner, StepRunResult
from app.modules.market_data.trading_calendar import UsEquitiesTradingCalendar
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
    if daily_due_slot is None and smoke_test_due_slot is None:
        return PaperSchedulerTickResult(
            results=[],
            skipped=[],
            errors=[],
            due_slot=None,
        )

    session_factory = session_factory or create_session_factory()
    step_runner = step_runner or PaperTradingStepRunner(session_factory=session_factory)
    with session_factory() as session:
        repository = ExperimentRepository(session)
        scheduled_experiments: list[tuple[int, datetime]] = []
        if daily_due_slot is not None:
            scheduled_experiments.extend(
                (experiment_id, daily_due_slot)
                for experiment_id in repository.list_paper_scheduler_eligible_experiment_ids()
            )
        if smoke_test_due_slot is not None:
            scheduled_experiments.extend(
                (experiment_id, smoke_test_due_slot)
                for experiment_id in (
                    repository.list_paper_smoke_test_scheduler_eligible_experiment_ids()
                )
            )

    results: list[StepRunResult] = []
    skipped: list[ScheduledStepSkip] = []
    errors: list[ScheduledStepError] = []
    for experiment_id, due_slot in scheduled_experiments:
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
        due_slot=daily_due_slot or smoke_test_due_slot,
    )


def sync_open_paper_broker_orders(
    *,
    sync_service: PaperBrokerSyncService | None = None,
) -> BrokerSyncRunResult:
    sync_service = sync_service or PaperBrokerSyncService()
    return sync_service.sync_open_orders()


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


def _parse_hh_mm(value: str) -> tuple[int, int]:
    hour, minute = value.split(":")
    return int(hour), int(minute)
