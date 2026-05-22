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
    OrderSide,
    OrderStatus,
    StrategyType,
    SystemEventType,
    TradeAction,
    TradingFrequency,
)
from app.modules.execution.orchestrator import HistoricalMovingAverageOrchestrator
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
    moving_average_window: int | None = 3,
) -> int:
    now = datetime(2026, 1, 1, 12, 0, 0)
    experiment = ExperimentModel(
        name="M4 integration",
        mode=ExperimentMode.HISTORICAL_SIMULATION,
        strategy_type=StrategyType.MOVING_AVERAGE,
        asset_symbol="SPY",
        status=ExperimentStatus.RUNNING,
        initial_capital=initial_capital,
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 10),
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
            strategy_type=StrategyType.MOVING_AVERAGE,
            strategy_version="moving-average-v1",
            moving_average_window=moving_average_window,
            position_sizing_type="ALL_IN",
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


def test_moving_average_orchestrator_persists_buy_hold_sell_audit_chain(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    HistoricalMovingAverageOrchestrator(session_factory=session_factory).run(
        experiment_id
    )

    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        portfolio = session.scalar(
            select(PortfolioModel).where(PortfolioModel.experiment_id == experiment_id)
        )
        assert experiment is not None
        assert portfolio is not None
        assert experiment.status is ExperimentStatus.COMPLETED
        assert portfolio.position_symbol is None
        assert portfolio.position_quantity == Decimal("0E-8")
        assert portfolio.cash == Decimal("9916.0000")
        assert portfolio.current_portfolio_value == Decimal("9916.0000")

        assert _count(session, ExecutionStepModel, experiment_id) == 7
        assert _count(session, MarketDataSnapshotModel, experiment_id) == 7
        assert _count(session, TradingDecisionModel, experiment_id) == 7
        assert _count(session, RiskCheckModel, experiment_id) == 7
        assert _count(session, PortfolioSnapshotModel, experiment_id) == 7
        assert _count(session, MetricSnapshotModel, experiment_id) == 7
        assert _count(session, OrderModel, experiment_id) == 2
        assert _count(session, TradeModel, experiment_id) == 2

        market_data = list(
            session.scalars(
                select(MarketDataSnapshotModel)
                .where(MarketDataSnapshotModel.experiment_id == experiment_id)
                .order_by(MarketDataSnapshotModel.timestamp)
            )
        )
        assert market_data[0].moving_average is None
        assert market_data[1].moving_average is None
        assert market_data[2].moving_average == Decimal("472.00000000")
        assert market_data[2].close == Decimal("473.00000000")
        assert market_data[2].raw_data_json["close"] == "473.00"

        decisions = list(
            session.scalars(
                select(TradingDecisionModel)
                .where(TradingDecisionModel.experiment_id == experiment_id)
                .order_by(TradingDecisionModel.id)
            )
        )
        assert [decision.action for decision in decisions] == [
            TradeAction.HOLD,
            TradeAction.HOLD,
            TradeAction.BUY,
            TradeAction.HOLD,
            TradeAction.HOLD,
            TradeAction.SELL,
            TradeAction.HOLD,
        ]
        assert "unavailable" in decisions[0].reason

        risk_checks = list(
            session.scalars(
                select(RiskCheckModel)
                .where(RiskCheckModel.experiment_id == experiment_id)
                .order_by(RiskCheckModel.id)
            )
        )
        assert [risk_check.final_action for risk_check in risk_checks] == [
            FinalAction.HOLD,
            FinalAction.HOLD,
            FinalAction.BUY,
            FinalAction.HOLD,
            FinalAction.HOLD,
            FinalAction.SELL,
            FinalAction.HOLD,
        ]

        orders = list(
            session.scalars(
                select(OrderModel)
                .where(OrderModel.experiment_id == experiment_id)
                .order_by(OrderModel.id)
            )
        )
        trades = list(
            session.scalars(
                select(TradeModel)
                .where(TradeModel.experiment_id == experiment_id)
                .order_by(TradeModel.id)
            )
        )
        assert [order.side for order in orders] == [OrderSide.BUY, OrderSide.SELL]
        assert all(order.status is OrderStatus.FILLED for order in orders)
        assert [trade.side for trade in trades] == [OrderSide.BUY, OrderSide.SELL]
        assert trades[0].quantity == trades[1].quantity == Decimal("21.00000000")

        event_types = set(
            session.scalars(
                select(SystemEventLogModel.event_type).where(
                    SystemEventLogModel.experiment_id == experiment_id
                )
            )
        )
        assert SystemEventType.EXPERIMENT_COMPLETED in event_types


def test_moving_average_insufficient_cash_holds_without_order(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session, initial_capital=Decimal("100.0000")
        )

    HistoricalMovingAverageOrchestrator(session_factory=session_factory).run(
        experiment_id
    )

    with session_factory() as session:
        risk_checks = list(
            session.scalars(
                select(RiskCheckModel)
                .where(RiskCheckModel.experiment_id == experiment_id)
                .order_by(RiskCheckModel.id)
            )
        )
        assert risk_checks[2].final_action is FinalAction.HOLD
        assert risk_checks[2].rejection_reason is not None
        assert "Insufficient cash" in risk_checks[2].rejection_reason
        assert _count(session, OrderModel, experiment_id) == 0
        assert _count(session, TradeModel, experiment_id) == 0


def test_moving_average_default_window_holds_until_200_bars(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session, moving_average_window=None)

    HistoricalMovingAverageOrchestrator(session_factory=session_factory).run(
        experiment_id
    )

    with session_factory() as session:
        assert _count(session, OrderModel, experiment_id) == 0
        assert _count(session, TradeModel, experiment_id) == 0
        decisions = list(
            session.scalars(
                select(TradingDecisionModel).where(
                    TradingDecisionModel.experiment_id == experiment_id
                )
            )
        )
        assert all(decision.action is TradeAction.HOLD for decision in decisions)


def test_moving_average_orchestrator_marks_current_step_failed(
    database_url: str, monkeypatch
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    calls = 0

    def fail_after_step(_, experiment_id, bar, execution_step_id, moving_average, window):
        nonlocal calls
        calls += 1
        raise RuntimeError("forced moving average failure")

    monkeypatch.setattr(HistoricalMovingAverageOrchestrator, "_run_step", fail_after_step)

    with pytest.raises(RuntimeError, match="forced moving average failure"):
        HistoricalMovingAverageOrchestrator(session_factory=session_factory).run(
            experiment_id
        )
    assert calls == 1

    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        step = session.scalar(
            select(ExecutionStepModel).where(
                ExecutionStepModel.experiment_id == experiment_id
            )
        )
        event = session.scalar(
            select(SystemEventLogModel).where(
                SystemEventLogModel.experiment_id == experiment_id,
                SystemEventLogModel.event_type == SystemEventType.EXPERIMENT_FAILED,
            )
        )
        assert experiment is not None
        assert step is not None
        assert event is not None
        assert experiment.status is ExperimentStatus.FAILED
        assert step.status is ExecutionStepStatus.FAILED
        assert event.level is EventLevel.ERROR
        assert event.execution_step_id == step.id
