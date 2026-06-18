from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ExperimentStepAlreadyRunningAppError
from app.domain.enums import (
    ExecutionStepStatus,
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    FinalAction,
    OrderSide,
    StrategyType,
    SystemEventType,
    TradeAction,
    TradingFrequency,
    TriggerType,
)
from app.modules.execution.step_runner import HistoricalStepRunner
from app.persistence.database import create_session_factory
from app.persistence.models import (
    ExecutionStepModel,
    ExperimentModel,
    MarketDataSnapshotModel,
    MetricSnapshotModel,
    OrderModel,
    PortfolioModel,
    PortfolioSnapshotModel,
    RiskCheckModel,
    StrategyConfigModel,
    SystemEventLogModel,
    TradeModel,
    TradingDecisionModel,
)


def _create_experiment(
    session: Session,
    *,
    strategy_type: StrategyType = StrategyType.BUY_AND_HOLD,
    initial_capital: Decimal = Decimal("10000.0000"),
    start_date: date = date(2024, 1, 2),
    end_date: date = date(2024, 1, 5),
    moving_average_window: int | None = None,
) -> int:
    now = datetime(2026, 1, 1, 12, 0, 0)
    experiment = ExperimentModel(
        name="M7a manual step",
        mode=ExperimentMode.HISTORICAL_SIMULATION,
        strategy_type=strategy_type,
        asset_symbol="SPY",
        status=ExperimentStatus.RUNNING,
        initial_capital=initial_capital,
        start_date=start_date,
        end_date=end_date,
        trading_frequency=TradingFrequency.DAILY,
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
            moving_average_window=moving_average_window,
            agent_mode=None,
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
            cash=initial_capital,
            position_symbol=None,
            position_quantity=Decimal("0"),
            current_price=None,
            current_position_value=Decimal("0"),
            current_portfolio_value=initial_capital,
            updated_at=now,
        )
    )
    session.commit()
    return experiment.id


def _count(session: Session, model, experiment_id: int) -> int:
    return int(
        session.scalar(
            select(func.count(model.id)).where(model.experiment_id == experiment_id)
        )
        or 0
    )


def test_buy_and_hold_manual_steps_advance_one_bar_at_a_time(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    runner = HistoricalStepRunner(session_factory=session_factory)

    first_result = runner.run_next_step(experiment_id)
    second_result = runner.run_next_step(experiment_id)

    assert first_result.execution_step_id is not None
    assert first_result.status is ExecutionStepStatus.COMPLETED
    assert second_result.execution_step_id is not None
    assert second_result.status is ExecutionStepStatus.COMPLETED

    with session_factory() as session:
        steps = list(
            session.scalars(
                select(ExecutionStepModel)
                .where(ExecutionStepModel.experiment_id == experiment_id)
                .order_by(ExecutionStepModel.sequence_number)
            )
        )
        assert [step.sequence_number for step in steps] == [1, 2]
        assert all(step.trigger_type is TriggerType.MANUAL for step in steps)
        assert all(step.status is ExecutionStepStatus.COMPLETED for step in steps)
        assert steps[0].scheduled_for == datetime(2024, 1, 2)
        assert steps[1].scheduled_for == datetime(2024, 1, 3)

        assert _count(session, MarketDataSnapshotModel, experiment_id) == 2
        assert _count(session, TradingDecisionModel, experiment_id) == 2
        assert _count(session, RiskCheckModel, experiment_id) == 2
        assert _count(session, PortfolioSnapshotModel, experiment_id) == 2
        assert _count(session, MetricSnapshotModel, experiment_id) == 2
        assert _count(session, OrderModel, experiment_id) == 1
        assert _count(session, TradeModel, experiment_id) == 1

        decisions = list(
            session.scalars(
                select(TradingDecisionModel)
                .where(TradingDecisionModel.experiment_id == experiment_id)
                .order_by(TradingDecisionModel.id)
            )
        )
        assert [decision.action for decision in decisions] == [
            TradeAction.BUY,
            TradeAction.HOLD,
        ]


def test_manual_step_marks_experiment_completed_after_final_bar(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 2),
        )

    result = HistoricalStepRunner(session_factory=session_factory).run_next_step(
        experiment_id
    )

    assert result.execution_step_id is not None
    assert result.status is ExecutionStepStatus.COMPLETED

    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        assert experiment is not None
        assert experiment.status is ExperimentStatus.COMPLETED
        assert _count(session, ExecutionStepModel, experiment_id) == 1
        event_types = set(
            session.scalars(
                select(SystemEventLogModel.event_type).where(
                    SystemEventLogModel.experiment_id == experiment_id
                )
            )
        )
        assert SystemEventType.EXPERIMENT_COMPLETED in event_types


def test_manual_step_no_remaining_bars_completes_without_new_step(
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
                trigger_type=TriggerType.MANUAL,
                sequence_number=1,
                error_message=None,
                created_at=datetime(2026, 1, 1, 12, 0, 0),
            )
        )
        session.commit()

    result = HistoricalStepRunner(session_factory=session_factory).run_next_step(
        experiment_id
    )

    assert result.execution_step_id is None
    assert result.status is ExperimentStatus.COMPLETED

    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        assert experiment is not None
        assert experiment.status is ExperimentStatus.COMPLETED
        assert _count(session, ExecutionStepModel, experiment_id) == 1


def test_moving_average_manual_steps_include_early_hold_buy_and_sell(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            strategy_type=StrategyType.MOVING_AVERAGE,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 10),
            moving_average_window=3,
        )

    runner = HistoricalStepRunner(session_factory=session_factory)
    for _ in range(6):
        runner.run_next_step(experiment_id)

    with session_factory() as session:
        decisions = list(
            session.scalars(
                select(TradingDecisionModel)
                .where(TradingDecisionModel.experiment_id == experiment_id)
                .order_by(TradingDecisionModel.id)
            )
        )
        risk_checks = list(
            session.scalars(
                select(RiskCheckModel)
                .where(RiskCheckModel.experiment_id == experiment_id)
                .order_by(RiskCheckModel.id)
            )
        )
        orders = list(
            session.scalars(
                select(OrderModel)
                .where(OrderModel.experiment_id == experiment_id)
                .order_by(OrderModel.id)
            )
        )
        assert [decision.action for decision in decisions] == [
            TradeAction.HOLD,
            TradeAction.HOLD,
            TradeAction.BUY,
            TradeAction.HOLD,
            TradeAction.HOLD,
            TradeAction.SELL,
        ]
        assert [risk_check.final_action for risk_check in risk_checks] == [
            FinalAction.HOLD,
            FinalAction.HOLD,
            FinalAction.BUY,
            FinalAction.HOLD,
            FinalAction.HOLD,
            FinalAction.SELL,
        ]
        assert [order.side for order in orders] == [OrderSide.BUY, OrderSide.SELL]


def test_running_step_blocks_manual_step(database_url: str) -> None:
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
                trigger_type=TriggerType.MANUAL,
                sequence_number=1,
                error_message=None,
                created_at=datetime(2026, 1, 1, 12, 0, 0),
            )
        )
        session.commit()

    with pytest.raises(ExperimentStepAlreadyRunningAppError):
        HistoricalStepRunner(session_factory=session_factory).run_next_step(
            experiment_id
        )


def test_failure_after_step_creation_marks_step_and_experiment_failed(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    calls = 0

    def fail_after_step(*args, **kwargs) -> None:
        nonlocal calls
        calls += 1
        raise RuntimeError("forced step failure")

    monkeypatch.setattr(HistoricalStepRunner, "_run_step_artifacts", fail_after_step)

    with pytest.raises(RuntimeError, match="forced step failure"):
        HistoricalStepRunner(session_factory=session_factory).run_next_step(
            experiment_id
        )
    assert calls == 1

    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        assert experiment is not None
        assert experiment.status is ExperimentStatus.FAILED

        step = session.scalar(
            select(ExecutionStepModel).where(
                ExecutionStepModel.experiment_id == experiment_id
            )
        )
        assert step is not None
        assert step.status is ExecutionStepStatus.FAILED
        assert step.error_message == "Manual historical execution step failed."

        event = session.scalar(
            select(SystemEventLogModel).where(
                SystemEventLogModel.experiment_id == experiment_id,
                SystemEventLogModel.event_type == SystemEventType.EXPERIMENT_FAILED,
            )
        )
        assert event is not None
