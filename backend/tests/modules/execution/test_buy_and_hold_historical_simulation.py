from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import (
    EventLevel,
    ExecutionStepStatus,
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    FinalAction,
    OrderStatus,
    StrategyType,
    SystemEventType,
    TradingFrequency,
)
from app.modules.execution.orchestrator import HistoricalBuyAndHoldOrchestrator
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
    initial_capital: Decimal = Decimal("10000.0000"),
) -> int:
    now = datetime(2026, 1, 1, 12, 0, 0)
    experiment = ExperimentModel(
        name="M3 integration",
        mode=ExperimentMode.HISTORICAL_SIMULATION,
        strategy_type=StrategyType.BUY_AND_HOLD,
        asset_symbol="SPY",
        status=ExperimentStatus.RUNNING,
        initial_capital=initial_capital,
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 5),
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
            strategy_type=StrategyType.BUY_AND_HOLD,
            moving_average_window=None,
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


def test_buy_and_hold_historical_orchestrator_persists_full_audit_chain(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    HistoricalBuyAndHoldOrchestrator(session_factory=session_factory).run(experiment_id)

    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        portfolio = session.scalar(
            select(PortfolioModel).where(PortfolioModel.experiment_id == experiment_id)
        )
        assert experiment is not None
        assert portfolio is not None
        assert experiment.status is ExperimentStatus.COMPLETED
        assert portfolio.cash == Decimal("109.0000")
        assert portfolio.position_quantity == Decimal("21.00000000")
        assert portfolio.current_portfolio_value == Decimal("10063.0000")

        assert _count(session, ExecutionStepModel, experiment_id) == 4
        assert _count(session, MarketDataSnapshotModel, experiment_id) == 4
        assert _count(session, TradingDecisionModel, experiment_id) == 4
        assert _count(session, RiskCheckModel, experiment_id) == 4
        assert _count(session, PortfolioSnapshotModel, experiment_id) == 4
        assert _count(session, MetricSnapshotModel, experiment_id) == 4
        assert _count(session, OrderModel, experiment_id) == 1
        assert _count(session, TradeModel, experiment_id) == 1

        order = session.scalar(
            select(OrderModel).where(OrderModel.experiment_id == experiment_id)
        )
        trade = session.scalar(
            select(TradeModel).where(TradeModel.experiment_id == experiment_id)
        )
        assert order is not None
        assert trade is not None
        assert order.status is OrderStatus.FILLED
        assert order.quantity == Decimal("21.00000000")
        assert trade.order_id == order.id

        metrics = list(
            session.scalars(
                select(MetricSnapshotModel)
                .where(MetricSnapshotModel.experiment_id == experiment_id)
                .order_by(MetricSnapshotModel.timestamp)
            )
        )
        assert metrics[-1].profit_loss == Decimal("63.0000")
        assert metrics[-1].total_return == Decimal("0.00630000")
        assert metrics[-1].number_of_trades == 1
        assert metrics[-1].max_drawdown == Decimal("0E-8")
        assert metrics[-1].buy_and_hold_return == Decimal("0.00630000")
        assert metrics[-1].difference_to_buy_and_hold == Decimal("0E-8")

        event_types = set(
            session.scalars(
                select(SystemEventLogModel.event_type).where(
                    SystemEventLogModel.experiment_id == experiment_id
                )
            )
        )
        assert SystemEventType.EXPERIMENT_COMPLETED in event_types


def test_insufficient_cash_converts_buy_to_hold(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session, initial_capital=Decimal("100.0000")
        )

    HistoricalBuyAndHoldOrchestrator(session_factory=session_factory).run(experiment_id)

    with session_factory() as session:
        risk_checks = list(
            session.scalars(
                select(RiskCheckModel)
                .where(RiskCheckModel.experiment_id == experiment_id)
                .order_by(RiskCheckModel.id)
            )
        )
        assert risk_checks[0].final_action is FinalAction.HOLD
        assert risk_checks[0].rejection_reason is not None
        assert "Insufficient cash" in risk_checks[0].rejection_reason
        assert risk_checks[0].rules_triggered_json["reason"] == (
            "INSUFFICIENT_CASH_FOR_ONE_SHARE"
        )
        assert _count(session, OrderModel, experiment_id) == 0
        assert _count(session, TradeModel, experiment_id) == 0


def test_orchestrator_persists_failure_state_before_step_created(
    database_url: str, monkeypatch
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    calls = 0

    def fail_before_step(_, experiment_id, bar):
        nonlocal calls
        calls += 1
        raise RuntimeError("forced failure")

    monkeypatch.setattr(
        HistoricalBuyAndHoldOrchestrator, "_create_running_step", fail_before_step
    )

    with pytest.raises(RuntimeError, match="forced failure"):
        HistoricalBuyAndHoldOrchestrator(session_factory=session_factory).run(
            experiment_id
        )
    assert calls == 1

    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        assert experiment is not None
        assert experiment.status is ExperimentStatus.FAILED
        assert _count(session, ExecutionStepModel, experiment_id) == 0
        event = session.scalar(
            select(SystemEventLogModel).where(
                SystemEventLogModel.experiment_id == experiment_id,
                SystemEventLogModel.event_type == SystemEventType.EXPERIMENT_FAILED,
            )
        )
        assert event is not None
        assert event.level is EventLevel.ERROR


def test_orchestrator_marks_current_step_failed_after_step_created(
    database_url: str, monkeypatch
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    calls = 0

    def fail_after_step(_, experiment_id, bar, execution_step_id):
        nonlocal calls
        calls += 1
        raise RuntimeError("forced failure")

    monkeypatch.setattr(HistoricalBuyAndHoldOrchestrator, "_run_step", fail_after_step)

    with pytest.raises(RuntimeError, match="forced failure"):
        HistoricalBuyAndHoldOrchestrator(session_factory=session_factory).run(
            experiment_id
        )
    assert calls == 1

    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        steps = list(
            session.scalars(
                select(ExecutionStepModel).where(
                    ExecutionStepModel.experiment_id == experiment_id
                )
            )
        )
        assert experiment is not None
        assert experiment.status is ExperimentStatus.FAILED
        assert len(steps) == 1
        assert steps[0].status is ExecutionStepStatus.FAILED
        event = session.scalar(
            select(SystemEventLogModel).where(
                SystemEventLogModel.experiment_id == experiment_id,
                SystemEventLogModel.event_type == SystemEventType.EXPERIMENT_FAILED,
            )
        )
        assert event is not None
        assert event.execution_step_id == steps[0].id
