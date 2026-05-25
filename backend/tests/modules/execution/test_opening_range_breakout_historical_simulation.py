from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import (
    EventLevel,
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    FinalAction,
    OrderSide,
    StrategyType,
    SystemEventType,
    TradingFrequency,
)
from app.modules.execution.orchestrator import HistoricalOpeningRangeBreakoutOrchestrator
from app.modules.market_data.intraday_csv_loader import EXPECTED_BARS_PER_SESSION
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
    start_date: date = date(2024, 1, 2),
    end_date: date = date(2024, 1, 3),
    position_sizing_type: str = "ALL_IN",
    position_sizing_value: Decimal | None = None,
    initial_capital: Decimal = Decimal("10000.0000"),
) -> int:
    now = datetime(2026, 1, 1, 12, 0, 0)
    experiment = ExperimentModel(
        name="M16 ORB integration",
        mode=ExperimentMode.HISTORICAL_SIMULATION,
        strategy_type=StrategyType.OPENING_RANGE_BREAKOUT,
        asset_symbol="SPY",
        status=ExperimentStatus.RUNNING,
        initial_capital=initial_capital,
        start_date=start_date,
        end_date=end_date,
        trading_frequency=TradingFrequency.INTRADAY_5_MIN,
        fee_model_type=FeeModelType.NONE,
        fee_value=Decimal("0"),
        created_at=now,
        updated_at=now,
    )
    session.add(experiment)
    session.flush()
    parameters_json = {"riskConfig": {"fallbackAction": "HOLD"}}
    if position_sizing_value is not None:
        parameters_json["positionSizingValue"] = float(position_sizing_value)
    session.add(
        StrategyConfigModel(
            experiment_id=experiment.id,
            strategy_type=StrategyType.OPENING_RANGE_BREAKOUT,
            strategy_version="opening-range-breakout-v1",
            moving_average_window=None,
            position_sizing_type=position_sizing_type,
            agent_mode=None,
            model_name=None,
            confidence_threshold=None,
            parameters_json=parameters_json,
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
    session.add(
        SystemEventLogModel(
            execution_step_id=None,
            experiment_id=experiment.id,
            timestamp=now,
            level=EventLevel.INFO,
            event_type=SystemEventType.EXPERIMENT_STARTED,
            message="Experiment started.",
            details_json={"experimentId": experiment.id},
            created_at=now,
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


def test_opening_range_breakout_full_run_persists_audit_chain(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    HistoricalOpeningRangeBreakoutOrchestrator(
        session_factory=session_factory
    ).run(experiment_id)

    expected_steps = EXPECTED_BARS_PER_SESSION * 2
    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        portfolio = session.scalar(
            select(PortfolioModel).where(PortfolioModel.experiment_id == experiment_id)
        )
        assert experiment is not None
        assert portfolio is not None
        assert experiment.status is ExperimentStatus.COMPLETED
        assert portfolio.position_quantity == Decimal("0E-8")
        assert portfolio.position_symbol is None

        assert _count(session, ExecutionStepModel, experiment_id) == expected_steps
        assert _count(session, MarketDataSnapshotModel, experiment_id) == expected_steps
        assert _count(session, TradingDecisionModel, experiment_id) == expected_steps
        assert _count(session, RiskCheckModel, experiment_id) == expected_steps
        assert _count(session, PortfolioSnapshotModel, experiment_id) == expected_steps
        assert _count(session, MetricSnapshotModel, experiment_id) == expected_steps

        orders = list(
            session.scalars(
                select(OrderModel)
                .where(OrderModel.experiment_id == experiment_id)
                .order_by(OrderModel.submitted_at)
            )
        )
        trades = list(
            session.scalars(
                select(TradeModel)
                .where(TradeModel.experiment_id == experiment_id)
                .order_by(TradeModel.timestamp)
            )
        )
        assert [order.side for order in orders] == [
            OrderSide.BUY,
            OrderSide.SELL,
            OrderSide.BUY,
            OrderSide.SELL,
        ]
        assert [trade.side for trade in trades] == [
            OrderSide.BUY,
            OrderSide.SELL,
            OrderSide.BUY,
            OrderSide.SELL,
        ]

        decisions = list(
            session.scalars(
                select(TradingDecisionModel)
                .where(TradingDecisionModel.experiment_id == experiment_id)
                .order_by(TradingDecisionModel.id)
            )
        )
        assert decisions[0].action.value == "HOLD"
        assert decisions[6].action.value == "BUY"
        assert decisions[12].action.value == "SELL"
        assert decisions[-1].action.value == "SELL"
        assert decisions[6].raw_decision_json["openingRangeHigh"] == 101.0
        assert decisions[-1].raw_decision_json["eodExit"] is True

        event_types = list(
            session.scalars(
                select(SystemEventLogModel.event_type).where(
                    SystemEventLogModel.experiment_id == experiment_id
                )
            )
        )
        assert SystemEventType.EXPERIMENT_COMPLETED in event_types


def test_opening_range_breakout_fixed_quantity_sizing_is_used(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 2),
            position_sizing_type="FIXED_QUANTITY",
            position_sizing_value=Decimal("3"),
        )

    HistoricalOpeningRangeBreakoutOrchestrator(
        session_factory=session_factory
    ).run(experiment_id)

    with session_factory() as session:
        first_buy_risk = session.scalar(
            select(RiskCheckModel)
            .where(
                RiskCheckModel.experiment_id == experiment_id,
                RiskCheckModel.final_action == FinalAction.BUY,
            )
            .order_by(RiskCheckModel.id)
        )
        first_buy_order = session.scalar(
            select(OrderModel)
            .where(
                OrderModel.experiment_id == experiment_id,
                OrderModel.side == OrderSide.BUY,
            )
            .order_by(OrderModel.id)
        )
        assert first_buy_risk is not None
        assert first_buy_order is not None
        assert first_buy_risk.final_quantity == Decimal("3.00000000")
        assert first_buy_order.quantity == Decimal("3.00000000")
        assert first_buy_risk.rules_triggered_json["positionSizing"] == {
            "positionSizingType": "FIXED_QUANTITY",
            "positionSizingValue": 3.0,
            "requestedQuantity": 3.0,
            "finalQuantity": 3.0,
            "sizingReason": "FIXED_QUANTITY",
        }
