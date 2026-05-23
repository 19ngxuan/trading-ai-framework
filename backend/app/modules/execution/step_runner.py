from dataclasses import dataclass
from datetime import datetime, time, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.errors import (
    ExperimentStepAlreadyRunningAppError,
    InvalidExperimentConfigurationAppError,
    InvalidStatusAppError,
    NotFoundAppError,
)
from app.domain.enums import (
    EventLevel,
    ExecutionStepStatus,
    ExperimentMode,
    ExperimentStatus,
    StrategyType,
    SystemEventType,
    TradingFrequency,
    TriggerType,
)
from app.modules.execution.orchestrator import (
    HistoricalBuyAndHoldOrchestrator,
    HistoricalMovingAverageOrchestrator,
)
from app.modules.market_data.errors import (
    MarketDataProviderError,
    MarketDataUnavailableError,
)
from app.modules.market_data.factory import create_market_data_provider
from app.modules.market_data.provider import DailyBar, MarketDataProvider
from app.persistence.database import create_session_factory
from app.persistence.models import ExecutionStepModel, SystemEventLogModel
from app.persistence.repositories import (
    ExecutionStepRepository,
    ExperimentRepository,
    SystemEventLogRepository,
)


@dataclass(frozen=True)
class StepRunResult:
    experiment_id: int
    execution_step_id: int | None
    status: ExecutionStepStatus | ExperimentStatus
    message: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _bar_timestamp(bar: DailyBar) -> datetime:
    return datetime.combine(bar.date, time.min)


class HistoricalStepRunner:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        market_data_provider: MarketDataProvider | None = None,
        csv_loader: MarketDataProvider | None = None,
    ) -> None:
        self.session_factory = session_factory or create_session_factory()
        self.market_data_provider = (
            market_data_provider
            or csv_loader
            or create_market_data_provider(get_settings())
        )

    def run_next_step(
        self,
        experiment_id: int,
        trigger_type: TriggerType = TriggerType.MANUAL,
    ) -> StepRunResult:
        execution_step_id: int | None = None
        failure_step_id: int | None = None
        try:
            selected = self._select_bar_and_create_step(experiment_id, trigger_type)
            if selected is None:
                return StepRunResult(
                    experiment_id=experiment_id,
                    execution_step_id=None,
                    status=ExperimentStatus.COMPLETED,
                    message="Experiment completed; no remaining historical bars.",
                )

            bar, sequence_number, execution_step_id = selected
            failure_step_id = execution_step_id
            self._run_step_artifacts(experiment_id, bar, execution_step_id)
            failure_step_id = None
            if self._is_final_bar(experiment_id, sequence_number):
                self._complete_experiment(experiment_id)
            return StepRunResult(
                experiment_id=experiment_id,
                execution_step_id=execution_step_id,
                status=ExecutionStepStatus.COMPLETED,
                message="Manual execution step completed.",
            )
        except (
            ExperimentStepAlreadyRunningAppError,
            InvalidExperimentConfigurationAppError,
            InvalidStatusAppError,
            NotFoundAppError,
        ):
            raise
        except Exception as exc:
            self._persist_failure(experiment_id, failure_step_id, exc)
            raise

    def _select_bar_and_create_step(
        self, experiment_id: int, trigger_type: TriggerType
    ) -> tuple[DailyBar, int, int] | None:
        with self.session_factory() as session:
            experiment_repository = ExperimentRepository(session)
            execution_step_repository = ExecutionStepRepository(session)
            experiment = experiment_repository.get_by_id(experiment_id)
            if experiment is None:
                raise NotFoundAppError(
                    "Experiment was not found.",
                    details={"experimentId": experiment_id},
                )
            if experiment.status is not ExperimentStatus.RUNNING:
                raise InvalidStatusAppError(
                    "Experiment must be RUNNING to execute the next step.",
                    details={
                        "experimentId": experiment_id,
                        "status": experiment.status.value,
                    },
                )
            if (
                experiment.mode is not ExperimentMode.HISTORICAL_SIMULATION
                or experiment.strategy_type
                not in {StrategyType.BUY_AND_HOLD, StrategyType.MOVING_AVERAGE}
                or experiment.trading_frequency is not TradingFrequency.DAILY
            ):
                raise InvalidExperimentConfigurationAppError(
                    "Manual stepping supports only daily historical Buy-and-Hold and Moving Average experiments.",
                    details={
                        "experimentId": experiment_id,
                        "mode": experiment.mode.value,
                        "strategyType": experiment.strategy_type.value,
                        "tradingFrequency": experiment.trading_frequency.value,
                    },
                )

            lock_acquired = session.scalar(
                text("SELECT pg_try_advisory_xact_lock(:experiment_id)"),
                {"experiment_id": experiment_id},
            )
            if not lock_acquired:
                raise ExperimentStepAlreadyRunningAppError(
                    "Experiment already has a step in progress.",
                    details={"experimentId": experiment_id},
                )

            if execution_step_repository.has_running_step(experiment_id):
                raise ExperimentStepAlreadyRunningAppError(
                    "Experiment already has a step in progress.",
                    details={"experimentId": experiment_id},
                )

            bars = self.market_data_provider.load_range(
                experiment.start_date, experiment.end_date
            )
            next_index = execution_step_repository.max_sequence_number(experiment_id)
            if next_index >= len(bars):
                self._mark_completed_in_session(session, experiment_id)
                session.commit()
                return None

            bar = bars[next_index]
            sequence_number = next_index + 1
            now = _utcnow()
            execution_step = execution_step_repository.add(
                ExecutionStepModel(
                    experiment_id=experiment_id,
                    scheduled_for=_bar_timestamp(bar),
                    started_at=now,
                    completed_at=None,
                    status=ExecutionStepStatus.RUNNING,
                    trigger_type=trigger_type,
                    sequence_number=sequence_number,
                    error_message=None,
                    created_at=now,
                )
            )
            session.flush()
            execution_step_id = execution_step.id
            session.commit()
            return bar, sequence_number, execution_step_id

    def _run_step_artifacts(
        self, experiment_id: int, bar: DailyBar, execution_step_id: int
    ) -> None:
        strategy_type = self._strategy_type(experiment_id)
        if strategy_type is StrategyType.BUY_AND_HOLD:
            HistoricalBuyAndHoldOrchestrator(
                session_factory=self.session_factory,
                market_data_provider=self.market_data_provider,
            )._run_step(experiment_id, bar, execution_step_id)
            return

        orchestrator = HistoricalMovingAverageOrchestrator(
            session_factory=self.session_factory,
            market_data_provider=self.market_data_provider,
        )
        prices = self._prices_through_bar(experiment_id, bar)
        window = orchestrator._moving_average_window(experiment_id)
        moving_average = orchestrator._moving_average(prices, window)
        orchestrator._run_step(
            experiment_id,
            bar,
            execution_step_id,
            moving_average,
            window,
        )

    def _strategy_type(self, experiment_id: int) -> StrategyType:
        with self.session_factory() as session:
            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            if experiment is None:
                raise NotFoundAppError(
                    "Experiment was not found.",
                    details={"experimentId": experiment_id},
                )
            return experiment.strategy_type

    def _prices_through_bar(self, experiment_id: int, bar: DailyBar) -> list:
        with self.session_factory() as session:
            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            if experiment is None:
                raise NotFoundAppError(
                    "Experiment was not found.",
                    details={"experimentId": experiment_id},
                )
            bars = self.market_data_provider.load_range(
                experiment.start_date, experiment.end_date
            )
            prices = []
            for candidate in bars:
                prices.append(candidate.adjusted_close)
                if candidate.date == bar.date:
                    break
            return prices

    def _is_final_bar(self, experiment_id: int, sequence_number: int) -> bool:
        with self.session_factory() as session:
            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            if experiment is None:
                raise NotFoundAppError(
                    "Experiment was not found.",
                    details={"experimentId": experiment_id},
                )
            bars = self.market_data_provider.load_range(
                experiment.start_date, experiment.end_date
            )
            return sequence_number >= len(bars)

    def _complete_experiment(self, experiment_id: int) -> None:
        with self.session_factory() as session:
            self._mark_completed_in_session(session, experiment_id)
            session.commit()

    def _mark_completed_in_session(self, session: Session, experiment_id: int) -> None:
        now = _utcnow()
        experiment = ExperimentRepository(session).get_by_id(experiment_id)
        if experiment is None:
            raise NotFoundAppError(
                "Experiment was not found.",
                details={"experimentId": experiment_id},
            )
        if experiment.status is not ExperimentStatus.COMPLETED:
            experiment.status = ExperimentStatus.COMPLETED
            experiment.updated_at = now
            SystemEventLogRepository(session).add(
                SystemEventLogModel(
                    execution_step_id=None,
                    experiment_id=experiment_id,
                    timestamp=now,
                    level=EventLevel.INFO,
                    event_type=SystemEventType.EXPERIMENT_COMPLETED,
                    message="Experiment completed.",
                    details_json={"experimentId": experiment_id},
                    created_at=now,
                )
            )

    def _persist_failure(
        self,
        experiment_id: int,
        execution_step_id: int | None,
        exc: Exception | None = None,
    ) -> None:
        with self.session_factory() as session:
            now = _utcnow()
            if execution_step_id is not None:
                step = ExecutionStepRepository(session).get(execution_step_id)
                if step is not None:
                    step.status = ExecutionStepStatus.FAILED
                    step.completed_at = now
                    step.error_message = "Manual historical execution step failed."

            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            if experiment is not None:
                experiment.status = ExperimentStatus.FAILED
                experiment.updated_at = now
                SystemEventLogRepository(session).add(
                    SystemEventLogModel(
                        execution_step_id=execution_step_id,
                        experiment_id=experiment_id,
                        timestamp=now,
                        level=EventLevel.ERROR,
                        event_type=SystemEventType.EXPERIMENT_FAILED,
                        message="Experiment failed.",
                        details_json=self._failure_details(experiment_id, exc),
                        created_at=now,
                    )
                )
            session.commit()

    def _failure_details(self, experiment_id: int, exc: Exception | None) -> dict:
        details = {"experimentId": experiment_id}
        if isinstance(exc, MarketDataUnavailableError):
            details["errorCode"] = "MARKET_DATA_MISSING"
            details["providerDetails"] = exc.details
        elif isinstance(exc, MarketDataProviderError):
            details["errorCode"] = "MARKET_DATA_PROVIDER_ERROR"
            details["providerDetails"] = exc.details
        return details
