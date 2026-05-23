import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import ExperimentStepAlreadyRunningAppError
from app.domain.enums import TriggerType
from app.modules.execution.step_runner import HistoricalStepRunner, StepRunResult
from app.persistence.database import create_session_factory
from app.persistence.repositories import ExperimentRepository

logger = logging.getLogger(__name__)


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
