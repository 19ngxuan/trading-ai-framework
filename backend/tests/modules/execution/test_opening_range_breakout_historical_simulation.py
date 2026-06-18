from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
import pytest
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
from app.modules.market_data.alpaca_intraday_provider import (
    AlpacaIntradayMarketDataProvider,
)
from app.modules.market_data.errors import MarketDataUnavailableError
from app.modules.market_data.intraday_provider import EXPECTED_BARS_PER_SESSION
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

NEW_YORK_TZ = ZoneInfo("America/New_York")


def _create_experiment(
    session: Session,
    *,
    start_date: date = date(2024, 1, 2),
    end_date: date = date(2024, 1, 3),
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
    session.add(
        StrategyConfigModel(
            experiment_id=experiment.id,
            strategy_type=StrategyType.OPENING_RANGE_BREAKOUT,
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


def _alpaca_payload_bar(local_timestamp: datetime, close: str) -> dict:
    timestamp = (
        local_timestamp.replace(tzinfo=NEW_YORK_TZ)
        .astimezone(UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )
    close_decimal = Decimal(close)
    return {
        "t": timestamp,
        "o": str(close_decimal - Decimal("0.05")),
        "h": str(close_decimal + Decimal("0.20")),
        "l": str(close_decimal - Decimal("0.20")),
        "c": close,
        "v": "1000",
    }


def _alpaca_orb_session_payload() -> list[dict]:
    timestamp = datetime(2024, 1, 2, 9, 30)
    rows: list[dict] = []
    for index in range(EXPECTED_BARS_PER_SESSION):
        if index < 6:
            close = "100.00"
            high = Decimal("101.00") if index == 2 else Decimal("100.20")
            low = Decimal("99.00") if index == 3 else Decimal("99.80")
            row = _alpaca_payload_bar(timestamp, close)
            row["h"] = str(high)
            row["l"] = str(low)
        elif index == 6:
            row = _alpaca_payload_bar(timestamp, "101.50")
        elif index == 12:
            row = _alpaca_payload_bar(timestamp, "98.50")
        else:
            row = _alpaca_payload_bar(timestamp, "100.25")
        rows.append(row)
        timestamp += timedelta(minutes=5)
    return rows


def _alpaca_orb_early_close_payload() -> list[dict]:
    timestamp = datetime(2024, 7, 3, 9, 30)
    rows: list[dict] = []
    for index in range(42):
        if index < 6:
            close = "100.00"
            high = Decimal("101.00") if index == 2 else Decimal("100.20")
            low = Decimal("99.00") if index == 3 else Decimal("99.80")
            row = _alpaca_payload_bar(timestamp, close)
            row["h"] = str(high)
            row["l"] = str(low)
        elif index == 6:
            row = _alpaca_payload_bar(timestamp, "101.50")
        elif index == 41:
            row = _alpaca_payload_bar(timestamp, "102.00")
        else:
            row = _alpaca_payload_bar(timestamp, "100.25")
        rows.append(row)
        timestamp += timedelta(minutes=5)
    return rows


def _alpaca_intraday_provider(payload: list[dict]) -> AlpacaIntradayMarketDataProvider:
    return AlpacaIntradayMarketDataProvider(
        api_key_id="key",
        api_secret_key="secret",
        base_url="https://data.example.test",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"bars": payload})
            )
        ),
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
        buy_decisions = [
            decision for decision in decisions if decision.action.value == "BUY"
        ]
        sell_decisions = [
            decision for decision in decisions if decision.action.value == "SELL"
        ]
        assert len(buy_decisions) == 2
        assert len(sell_decisions) == 2
        assert buy_decisions[0].raw_decision_json["openingRangeHigh"] == 101.0

        event_types = list(
            session.scalars(
                select(SystemEventLogModel.event_type).where(
                    SystemEventLogModel.experiment_id == experiment_id
                )
            )
        )
        assert SystemEventType.EXPERIMENT_COMPLETED in event_types


def test_opening_range_breakout_uses_default_cash_based_buy_quantity(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 2),
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
        assert first_buy_risk.final_quantity == Decimal("98.00000000")
        assert first_buy_order.quantity == Decimal("98.00000000")
        assert first_buy_risk.rules_triggered_json["reason"] == (
            "DEFAULT_WHOLE_SHARE_BUY"
        )


def test_opening_range_breakout_accepts_injected_alpaca_intraday_provider(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 2),
        )

    HistoricalOpeningRangeBreakoutOrchestrator(
        session_factory=session_factory,
        intraday_provider=_alpaca_intraday_provider(_alpaca_orb_session_payload()),
    ).run(experiment_id)

    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        first_snapshot = session.scalar(
            select(MarketDataSnapshotModel)
            .where(MarketDataSnapshotModel.experiment_id == experiment_id)
            .order_by(MarketDataSnapshotModel.timestamp)
        )
        assert experiment is not None
        assert experiment.status is ExperimentStatus.COMPLETED
        assert first_snapshot is not None
        assert first_snapshot.raw_data_json["provider"] == "alpaca_intraday"
        assert _count(session, ExecutionStepModel, experiment_id) == 78
        assert _count(session, OrderModel, experiment_id) == 2
        assert _count(session, TradeModel, experiment_id) == 2


def test_opening_range_breakout_alpaca_missing_data_fails_before_orders(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 2),
        )

    provider = _alpaca_intraday_provider(_alpaca_orb_session_payload()[1:])
    with pytest.raises(MarketDataUnavailableError):
        HistoricalOpeningRangeBreakoutOrchestrator(
            session_factory=session_factory,
            intraday_provider=provider,
        ).run(experiment_id)

    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        event = session.scalar(
            select(SystemEventLogModel)
            .where(
                SystemEventLogModel.experiment_id == experiment_id,
                SystemEventLogModel.event_type == SystemEventType.EXPERIMENT_FAILED,
            )
            .order_by(SystemEventLogModel.id.desc())
        )
        assert experiment is not None
        assert experiment.status is ExperimentStatus.FAILED
        assert event is not None
        assert event.details_json["errorCode"] == "MARKET_DATA_MISSING"
        assert _count(session, ExecutionStepModel, experiment_id) == 0
        assert _count(session, OrderModel, experiment_id) == 0
        assert _count(session, TradeModel, experiment_id) == 0


def test_opening_range_breakout_early_close_exits_on_early_final_bar(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            start_date=date(2024, 7, 3),
            end_date=date(2024, 7, 3),
        )

    HistoricalOpeningRangeBreakoutOrchestrator(
        session_factory=session_factory,
        intraday_provider=_alpaca_intraday_provider(_alpaca_orb_early_close_payload()),
    ).run(experiment_id)

    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        decisions = list(
            session.scalars(
                select(TradingDecisionModel)
                .where(TradingDecisionModel.experiment_id == experiment_id)
                .order_by(TradingDecisionModel.id)
            )
        )
        assert experiment is not None
        assert experiment.status is ExperimentStatus.COMPLETED
        assert len(decisions) == 42
        assert decisions[-1].action.value == "SELL"
        assert decisions[-1].raw_decision_json["eodExit"] is True
        assert decisions[-1].created_at is not None
        assert _count(session, OrderModel, experiment_id) == 2
        last_snapshot = session.scalar(
            select(MarketDataSnapshotModel)
            .where(MarketDataSnapshotModel.experiment_id == experiment_id)
            .order_by(MarketDataSnapshotModel.timestamp.desc())
        )
        assert last_snapshot is not None
        assert last_snapshot.timestamp.isoformat() == "2024-07-03T12:55:00"


def test_opening_range_breakout_non_trading_range_completes_with_zero_steps(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            start_date=date(2024, 1, 6),
            end_date=date(2024, 1, 7),
        )

    HistoricalOpeningRangeBreakoutOrchestrator(
        session_factory=session_factory,
        intraday_provider=_alpaca_intraday_provider(
            [_alpaca_payload_bar(datetime(2024, 1, 6, 9, 30), "100.00")]
        ),
    ).run(experiment_id)

    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        event_types = list(
            session.scalars(
                select(SystemEventLogModel.event_type)
                .where(SystemEventLogModel.experiment_id == experiment_id)
                .order_by(SystemEventLogModel.id)
            )
        )
        assert experiment is not None
        assert experiment.status is ExperimentStatus.COMPLETED
        assert _count(session, ExecutionStepModel, experiment_id) == 0
        assert _count(session, MarketDataSnapshotModel, experiment_id) == 0
        assert _count(session, TradingDecisionModel, experiment_id) == 0
        assert _count(session, RiskCheckModel, experiment_id) == 0
        assert _count(session, OrderModel, experiment_id) == 0
        assert _count(session, TradeModel, experiment_id) == 0
        assert SystemEventType.EXPERIMENT_COMPLETED in event_types
