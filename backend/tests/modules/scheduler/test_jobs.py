from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ExperimentStepAlreadyRunningAppError
from app.domain.enums import (
    AgentMode,
    ExecutionStepStatus,
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    StrategyType,
    SystemEventType,
    TradingFrequency,
    TriggerType,
)
from app.modules.execution.step_runner import StepRunResult
from app.modules.market_data.errors import MarketDataUnavailableError
from app.modules.market_data.intraday_provider import IntradayBar
from app.modules.scheduler.jobs import (
    sync_open_paper_broker_orders,
    trigger_due_experiments,
    trigger_due_paper_trading_experiments,
)
from app.persistence.database import create_session_factory
from app.persistence.models import (
    ExecutionStepModel,
    ExperimentModel,
    PortfolioModel,
    StrategyConfigModel,
    SystemEventLogModel,
)


class FakeStepRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[int, TriggerType]] = []
        self.failures: dict[int, Exception] = {}

    def run_next_step(
        self, experiment_id: int, trigger_type: TriggerType = TriggerType.MANUAL
    ) -> StepRunResult:
        self.calls.append((experiment_id, trigger_type))
        if experiment_id in self.failures:
            raise self.failures[experiment_id]
        return StepRunResult(
            experiment_id=experiment_id,
            execution_step_id=experiment_id * 100,
            status=ExecutionStepStatus.COMPLETED,
            message="scheduled",
        )


class FakePaperStepRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[int, TriggerType, datetime | None]] = []
        self.failures: dict[int, Exception] = {}

    def run_next_step(
        self,
        experiment_id: int,
        trigger_type: TriggerType = TriggerType.MANUAL,
        scheduled_for: datetime | None = None,
    ) -> StepRunResult:
        self.calls.append((experiment_id, trigger_type, scheduled_for))
        if experiment_id in self.failures:
            raise self.failures[experiment_id]
        return StepRunResult(
            experiment_id=experiment_id,
            execution_step_id=experiment_id * 100,
            status=ExecutionStepStatus.COMPLETED,
            message="scheduled paper",
        )


class MissingIntradayProvider:
    def load_range(self, *args, **kwargs):
        return []

    def load_session_until(self, *args, **kwargs):
        raise MarketDataUnavailableError("Completed bar is unavailable.")


class HourlyIntradayProvider:
    def __init__(self) -> None:
        self.bars = [
            IntradayBar(
                timestamp=datetime(2026, 1, 2, hour, minute),
                session_date=date(2026, 1, 2),
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
                volume=Decimal("1000"),
                raw={"timestamp": datetime(2026, 1, 2, hour, minute).isoformat()},
            )
            for hour, minute in (
                (14, 30),
                (14, 35),
                (14, 40),
                (14, 45),
                (14, 50),
                (14, 55),
                (15, 0),
                (15, 5),
                (15, 10),
                (15, 15),
                (15, 20),
                (15, 25),
            )
        ]

    def load_range(self, *args, **kwargs):
        return self.bars

    def load_session_until(self, *args, **kwargs):
        return self.bars


def _create_experiment(
    session: Session,
    *,
    status: ExperimentStatus = ExperimentStatus.RUNNING,
    mode: ExperimentMode = ExperimentMode.HISTORICAL_SIMULATION,
    strategy_type: StrategyType = StrategyType.BUY_AND_HOLD,
    trading_frequency: TradingFrequency = TradingFrequency.DAILY,
    start_date: date = date(2024, 1, 2),
    end_date: date = date(2024, 1, 5),
    agent_mode: AgentMode | None = None,
) -> int:
    now = datetime(2026, 1, 1, 12, 0, 0)
    experiment = ExperimentModel(
        name="M7b scheduled experiment",
        mode=mode,
        strategy_type=strategy_type,
        asset_symbol="SPY",
        status=status,
        initial_capital=Decimal("10000.0000"),
        start_date=start_date,
        end_date=end_date,
        trading_frequency=trading_frequency,
        fee_model_type=FeeModelType.NONE,
        fee_value=Decimal("0"),
        created_at=now,
        updated_at=now,
    )
    session.add(experiment)
    session.flush()
    session.add(
        StrategyConfigModel(
            experiment_id=experiment.id,
            strategy_type=strategy_type,
            moving_average_window=3
            if strategy_type is StrategyType.MOVING_AVERAGE
            else None,
            agent_mode=agent_mode,
            model_name=None,
            confidence_threshold=None,
            parameters_json={"riskConfig": {"fallbackAction": "HOLD"}},
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        PortfolioModel(
            experiment_id=experiment.id,
            cash=Decimal("10000.0000"),
            position_symbol=None,
            position_quantity=Decimal("0"),
            current_price=None,
            current_position_value=Decimal("0"),
            current_portfolio_value=Decimal("10000.0000"),
            updated_at=now,
        )
    )
    session.commit()
    return experiment.id


def test_scheduler_job_selects_only_eligible_experiments(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        buy_and_hold_id = _create_experiment(session)
        moving_average_id = _create_experiment(
            session, strategy_type=StrategyType.MOVING_AVERAGE
        )
        _create_experiment(session, status=ExperimentStatus.CREATED)
        _create_experiment(session, status=ExperimentStatus.PAUSED)
        _create_experiment(session, status=ExperimentStatus.STOPPED)
        _create_experiment(session, status=ExperimentStatus.COMPLETED)
        _create_experiment(session, status=ExperimentStatus.FAILED)
        _create_experiment(session, mode=ExperimentMode.PAPER_TRADING)
        _create_experiment(session, strategy_type=StrategyType.AGENTIC_AI)
        _create_experiment(session, trading_frequency=TradingFrequency.WEEKLY)

    fake_runner = FakeStepRunner()

    result = trigger_due_experiments(
        session_factory=session_factory,
        step_runner=fake_runner,
    )

    assert fake_runner.calls == [
        (buy_and_hold_id, TriggerType.SCHEDULED),
        (moving_average_id, TriggerType.SCHEDULED),
    ]
    assert [item.experiment_id for item in result.results] == [
        buy_and_hold_id,
        moving_average_id,
    ]
    assert result.skipped == []
    assert result.errors == []


def test_scheduler_job_continues_after_running_step_conflict(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        first_id = _create_experiment(session)
        second_id = _create_experiment(session, strategy_type=StrategyType.MOVING_AVERAGE)

    fake_runner = FakeStepRunner()
    fake_runner.failures[first_id] = ExperimentStepAlreadyRunningAppError(
        "Experiment already has a step in progress.",
        details={"experimentId": first_id},
    )

    result = trigger_due_experiments(
        session_factory=session_factory,
        step_runner=fake_runner,
    )

    assert fake_runner.calls == [
        (first_id, TriggerType.SCHEDULED),
        (second_id, TriggerType.SCHEDULED),
    ]
    assert [item.experiment_id for item in result.skipped] == [first_id]
    assert result.skipped[0].error_code == "EXPERIMENT_STEP_ALREADY_RUNNING"
    assert [item.experiment_id for item in result.results] == [second_id]
    assert result.errors == []


def test_scheduler_job_treats_existing_running_step_as_skip(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)
        session.add(
            ExecutionStepModel(
                experiment_id=experiment_id,
                scheduled_for=datetime(2024, 1, 2),
                started_at=datetime(2026, 1, 1, 12, 0, 0),
                completed_at=None,
                status=ExecutionStepStatus.RUNNING,
                trigger_type=TriggerType.SCHEDULED,
                sequence_number=1,
                error_message=None,
                created_at=datetime(2026, 1, 1, 12, 0, 0),
            )
        )
        session.commit()

    result = trigger_due_experiments(session_factory=session_factory)

    assert result.results == []
    assert [item.experiment_id for item in result.skipped] == [experiment_id]
    assert result.skipped[0].error_code == "EXPERIMENT_STEP_ALREADY_RUNNING"
    assert result.errors == []


def test_scheduler_job_continues_after_unexpected_failure(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        first_id = _create_experiment(session)
        second_id = _create_experiment(session, strategy_type=StrategyType.MOVING_AVERAGE)

    fake_runner = FakeStepRunner()
    fake_runner.failures[first_id] = RuntimeError("forced scheduler failure")

    result = trigger_due_experiments(
        session_factory=session_factory,
        step_runner=fake_runner,
    )

    assert fake_runner.calls == [
        (first_id, TriggerType.SCHEDULED),
        (second_id, TriggerType.SCHEDULED),
    ]
    assert [item.experiment_id for item in result.errors] == [first_id]
    assert result.errors[0].error_type == "RuntimeError"
    assert [item.experiment_id for item in result.results] == [second_id]
    assert result.skipped == []


def test_scheduler_job_no_remaining_bars_marks_experiment_completed(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 2),
        )
        session.add(
            ExecutionStepModel(
                experiment_id=experiment_id,
                scheduled_for=datetime(2024, 1, 2),
                started_at=datetime(2026, 1, 1, 12, 0, 0),
                completed_at=datetime(2026, 1, 1, 12, 1, 0),
                status=ExecutionStepStatus.COMPLETED,
                trigger_type=TriggerType.SCHEDULED,
                sequence_number=1,
                error_message=None,
                created_at=datetime(2026, 1, 1, 12, 0, 0),
            )
        )
        session.commit()

    result = trigger_due_experiments(session_factory=session_factory)

    assert len(result.results) == 1
    assert result.results[0].experiment_id == experiment_id
    assert result.results[0].execution_step_id is None
    assert result.skipped == []
    assert result.errors == []

    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        assert experiment is not None
        assert experiment.status is ExperimentStatus.COMPLETED
        event = session.scalar(
            select(SystemEventLogModel).where(
                SystemEventLogModel.experiment_id == experiment_id,
                SystemEventLogModel.event_type == SystemEventType.EXPERIMENT_COMPLETED,
            )
        )
        assert event is not None


def test_paper_scheduler_job_selects_only_due_running_paper_experiments(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        paper_id = _create_experiment(session, mode=ExperimentMode.PAPER_TRADING)
        _create_experiment(
            session,
            mode=ExperimentMode.PAPER_TRADING,
            status=ExperimentStatus.PAUSED,
        )
        _create_experiment(
            session,
            mode=ExperimentMode.PAPER_TRADING,
            status=ExperimentStatus.STOPPED,
        )
        _create_experiment(session, mode=ExperimentMode.HISTORICAL_SIMULATION)
        moving_average_id = _create_experiment(
            session,
            mode=ExperimentMode.PAPER_TRADING,
            strategy_type=StrategyType.MOVING_AVERAGE,
        )
        agentic_ai_id = _create_experiment(
            session,
            mode=ExperimentMode.PAPER_TRADING,
            strategy_type=StrategyType.AGENTIC_AI,
            agent_mode=AgentMode.SINGLE_AGENT,
        )
        pipeline_daily_id = _create_experiment(
            session,
            mode=ExperimentMode.PAPER_TRADING,
            strategy_type=StrategyType.AGENTIC_AI,
            agent_mode=AgentMode.PIPELINE,
        )
        hourly_single_id = _create_experiment(
            session,
            mode=ExperimentMode.PAPER_TRADING,
            strategy_type=StrategyType.AGENTIC_AI,
            trading_frequency=TradingFrequency.HOURLY,
            agent_mode=AgentMode.SINGLE_AGENT,
        )
        hourly_pipeline_id = _create_experiment(
            session,
            mode=ExperimentMode.PAPER_TRADING,
            strategy_type=StrategyType.AGENTIC_AI,
            trading_frequency=TradingFrequency.HOURLY,
            agent_mode=AgentMode.PIPELINE,
        )
        _create_experiment(
            session,
            mode=ExperimentMode.PAPER_TRADING,
            trading_frequency=TradingFrequency.WEEKLY,
        )

    fake_runner = FakePaperStepRunner()
    result = trigger_due_paper_trading_experiments(
        session_factory=session_factory,
        step_runner=fake_runner,
        now=datetime(2026, 1, 2, 16, 5, tzinfo=ZoneInfo("America/New_York")),
        daily_evaluation_time="15:55",
        intraday_provider=HourlyIntradayProvider(),
    )

    assert result.due_slot == datetime(2026, 1, 2, 20, 55)
    assert fake_runner.calls == [
        (paper_id, TriggerType.SCHEDULED, datetime(2026, 1, 2, 20, 55)),
        (moving_average_id, TriggerType.SCHEDULED, datetime(2026, 1, 2, 20, 55)),
        (agentic_ai_id, TriggerType.SCHEDULED, datetime(2026, 1, 2, 20, 55)),
        (pipeline_daily_id, TriggerType.SCHEDULED, datetime(2026, 1, 2, 20, 55)),
        (hourly_single_id, TriggerType.SCHEDULED, datetime(2026, 1, 2, 19, 30)),
        (hourly_pipeline_id, TriggerType.SCHEDULED, datetime(2026, 1, 2, 19, 30)),
    ]
    assert [item.experiment_id for item in result.results] == [
        paper_id,
        moving_average_id,
        agentic_ai_id,
        pipeline_daily_id,
        hourly_single_id,
        hourly_pipeline_id,
    ]
    assert result.skipped == []
    assert result.errors == []


def test_paper_scheduler_skips_orb_when_completed_bar_is_unavailable(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        orb_id = _create_experiment(
            session,
            mode=ExperimentMode.PAPER_TRADING,
            strategy_type=StrategyType.OPENING_RANGE_BREAKOUT,
            trading_frequency=TradingFrequency.INTRADAY_5_MIN,
        )

    fake_runner = FakePaperStepRunner()
    result = trigger_due_paper_trading_experiments(
        session_factory=session_factory,
        step_runner=fake_runner,
        intraday_provider=MissingIntradayProvider(),
        now=datetime(2026, 1, 2, 10, 5, tzinfo=ZoneInfo("America/New_York")),
    )

    assert result.due_slot == datetime(2026, 1, 2, 10, 0)
    assert fake_runner.calls == []
    assert [item.experiment_id for item in result.skipped] == [orb_id]
    assert result.skipped[0].error_code == "PAPER_ORB_COMPLETED_BAR_UNAVAILABLE"
    with session_factory() as session:
        assert not list(
            session.scalars(
                select(ExecutionStepModel).where(
                    ExecutionStepModel.experiment_id == orb_id
                )
            )
        )


def test_paper_scheduler_selects_smoke_test_only_when_enabled_and_market_open(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        smoke_id = _create_experiment(
            session,
            mode=ExperimentMode.PAPER_TRADING,
            strategy_type=StrategyType.PAPER_TRADING_SMOKE_TEST,
            trading_frequency=TradingFrequency.TEST_1_MIN,
        )

    disabled_runner = FakePaperStepRunner()
    disabled = trigger_due_paper_trading_experiments(
        session_factory=session_factory,
        step_runner=disabled_runner,
        now=datetime(2026, 1, 2, 10, 5, 30, tzinfo=ZoneInfo("America/New_York")),
        paper_trading_test_mode_enabled=False,
    )

    assert disabled_runner.calls == []
    assert disabled.results == []

    enabled_runner = FakePaperStepRunner()
    enabled = trigger_due_paper_trading_experiments(
        session_factory=session_factory,
        step_runner=enabled_runner,
        now=datetime(2026, 1, 2, 10, 5, 30, tzinfo=ZoneInfo("America/New_York")),
        paper_trading_test_mode_enabled=True,
    )

    assert enabled.due_slot == datetime(2026, 1, 2, 15, 5)
    assert enabled_runner.calls == [
        (smoke_id, TriggerType.SCHEDULED, datetime(2026, 1, 2, 15, 5))
    ]
    assert [item.experiment_id for item in enabled.results] == [smoke_id]


def test_paper_scheduler_skips_smoke_test_outside_regular_market_hours(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        _create_experiment(
            session,
            mode=ExperimentMode.PAPER_TRADING,
            strategy_type=StrategyType.PAPER_TRADING_SMOKE_TEST,
            trading_frequency=TradingFrequency.TEST_1_MIN,
        )

    fake_runner = FakePaperStepRunner()
    result = trigger_due_paper_trading_experiments(
        session_factory=session_factory,
        step_runner=fake_runner,
        now=datetime(2026, 1, 2, 8, 30, tzinfo=ZoneInfo("America/New_York")),
        paper_trading_test_mode_enabled=True,
    )

    assert result.due_slot is None
    assert fake_runner.calls == []


def test_paper_scheduler_job_skips_before_due_time(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        _create_experiment(session, mode=ExperimentMode.PAPER_TRADING)

    fake_runner = FakePaperStepRunner()
    result = trigger_due_paper_trading_experiments(
        session_factory=session_factory,
        step_runner=fake_runner,
        now=datetime(2026, 1, 2, 15, 0, tzinfo=ZoneInfo("America/New_York")),
        daily_evaluation_time="15:55",
    )

    assert result.due_slot is None
    assert fake_runner.calls == []


def test_broker_sync_job_delegates_to_sync_service() -> None:
    class FakeSyncService:
        def __init__(self) -> None:
            self.called = False

        def sync_open_orders(self):
            self.called = True
            return "synced"

    service = FakeSyncService()

    assert sync_open_paper_broker_orders(sync_service=service) == "synced"
    assert service.called is True
