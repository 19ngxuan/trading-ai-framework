from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import (
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    StrategyType,
    SystemEventType,
    TradingFrequency,
)
from app.modules.execution.orchestrator import HistoricalBuyAndHoldOrchestrator
from app.modules.market_data.errors import MarketDataUnavailableError
from app.persistence.database import create_session_factory
from app.persistence.models import (
    ExperimentModel,
    OrderModel,
    PortfolioModel,
    StrategyConfigModel,
    SystemEventLogModel,
    TradeModel,
)


class UnavailableProvider:
    def load_range(self, *args, **kwargs):
        raise MarketDataUnavailableError(
            "No market data.",
            details={"symbol": "SPY"},
        )

    def get_latest_bar(self, symbol: str = "SPY"):
        raise MarketDataUnavailableError(
            "No market data.",
            details={"symbol": symbol},
        )


def _create_experiment(session: Session) -> int:
    now = datetime(2026, 1, 1, 12, 0, 0)
    experiment = ExperimentModel(
        name="M8 market data integration",
        mode=ExperimentMode.HISTORICAL_SIMULATION,
        strategy_type=StrategyType.BUY_AND_HOLD,
        asset_symbol="SPY",
        status=ExperimentStatus.RUNNING,
        initial_capital=Decimal("10000.0000"),
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
            strategy_version="buy-and-hold-v1",
            moving_average_window=None,
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


def _count(session: Session, model, experiment_id: int) -> int:
    return int(
        session.scalar(
            select(func.count(model.id)).where(model.experiment_id == experiment_id)
        )
        or 0
    )


def test_missing_market_data_fails_experiment_without_orders_or_trades(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    with pytest.raises(MarketDataUnavailableError):
        HistoricalBuyAndHoldOrchestrator(
            session_factory=session_factory,
            market_data_provider=UnavailableProvider(),
        ).run(experiment_id)

    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        assert experiment is not None
        assert experiment.status is ExperimentStatus.FAILED
        assert _count(session, OrderModel, experiment_id) == 0
        assert _count(session, TradeModel, experiment_id) == 0

        event = session.scalar(
            select(SystemEventLogModel).where(
                SystemEventLogModel.experiment_id == experiment_id,
                SystemEventLogModel.event_type == SystemEventType.EXPERIMENT_FAILED,
            )
        )
        assert event is not None
        assert event.details_json["errorCode"] == "MARKET_DATA_MISSING"
        assert event.details_json["providerDetails"] == {"symbol": "SPY"}
