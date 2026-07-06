from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.enums import (
    AgentMode,
    BrokerName,
    BrokerSyncStatus,
    DecisionSourceType,
    ExecutionStepStatus,
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    OrderMode,
    OrderSide,
    OrderStatus,
    OrderType,
    StrategyType,
    TradingFrequency,
    TradeAction,
    TriggerType,
    FinalAction,
)
from app.persistence.database import create_session_factory
from app.main import create_app
from app.persistence.models import (
    BrokerSyncLogModel,
    ExecutionStepModel,
    ExperimentModel,
    MarketDataSnapshotModel,
    OrderModel,
    PortfolioModel,
    RiskCheckModel,
    StrategyConfigModel,
    TradeModel,
    TradingDecisionModel,
)


def _create_paper_experiment(
    session: Session,
    *,
    status: ExperimentStatus,
    strategy_type: StrategyType = StrategyType.BUY_AND_HOLD,
    trading_frequency: TradingFrequency = TradingFrequency.DAILY,
) -> int:
    now = datetime(2026, 1, 1, 12, 0, 0)
    experiment = ExperimentModel(
        name="Paper Ops",
        mode=ExperimentMode.PAPER_TRADING,
        strategy_type=strategy_type,
        asset_symbol="SPY",
        status=status,
        initial_capital=Decimal("10000.0000"),
        start_date=now.date(),
        end_date=now.date(),
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


def _add_paper_artifacts(session: Session, experiment_id: int) -> None:
    now = datetime(2026, 1, 1, 15, 55, 0)
    step = ExecutionStepModel(
        experiment_id=experiment_id,
        scheduled_for=now,
        started_at=now,
        completed_at=now,
        status=ExecutionStepStatus.COMPLETED,
        trigger_type=TriggerType.SCHEDULED,
        sequence_number=1,
        error_message=None,
        created_at=now,
    )
    session.add(step)
    session.flush()
    market_data = MarketDataSnapshotModel(
        execution_step_id=step.id,
        experiment_id=experiment_id,
        timestamp=now,
        symbol="SPY",
        price=Decimal("500"),
        open=Decimal("499"),
        high=Decimal("501"),
        low=Decimal("498"),
        close=Decimal("500"),
        volume=Decimal("1000"),
        moving_average=None,
        rsi=None,
        raw_data_json={"source": "test"},
        created_at=now,
    )
    session.add(market_data)
    session.flush()
    decision = TradingDecisionModel(
        execution_step_id=step.id,
        experiment_id=experiment_id,
        market_data_snapshot_id=market_data.id,
        source_type=DecisionSourceType.STRATEGY,
        source_name="buy-and-hold-v1",
        action=TradeAction.BUY,
        symbol="SPY",
        suggested_quantity=None,
        suggested_notional=None,
        confidence=Decimal("1"),
        reason="test",
        raw_decision_json={},
        created_at=now,
    )
    session.add(decision)
    session.flush()
    risk = RiskCheckModel(
        execution_step_id=step.id,
        experiment_id=experiment_id,
        trading_decision_id=decision.id,
        approved=True,
        final_action=FinalAction.BUY,
        final_quantity=Decimal("1"),
        final_notional=Decimal("500"),
        rejection_reason=None,
        rules_triggered_json={},
        created_at=now,
    )
    session.add(risk)
    session.flush()
    order = OrderModel(
        execution_step_id=step.id,
        experiment_id=experiment_id,
        risk_check_id=risk.id,
        mode=OrderMode.PAPER_BROKER,
        broker_name=BrokerName.ALPACA,
        broker_order_id="paper-order-1",
        symbol="SPY",
        side=OrderSide.BUY,
        quantity=Decimal("1"),
        order_type=OrderType.MARKET,
        status=OrderStatus.SUBMITTED,
        submitted_at=now,
        filled_at=None,
        average_fill_price=None,
        error_message=None,
        created_at=now,
    )
    session.add(order)
    session.flush()
    session.add(
        TradeModel(
            execution_step_id=step.id,
            experiment_id=experiment_id,
            order_id=order.id,
            timestamp=now,
            symbol="SPY",
            side=OrderSide.BUY,
            quantity=Decimal("1"),
            price=Decimal("500"),
            order_value=Decimal("500"),
            fee=Decimal("0"),
            portfolio_value_after_trade=Decimal("10000"),
            created_at=now,
        )
    )
    session.add(
        BrokerSyncLogModel(
            execution_step_id=step.id,
            experiment_id=experiment_id,
            timestamp=now,
            broker_name=BrokerName.ALPACA,
            sync_status=BrokerSyncStatus.SUCCESS,
            broker_cash=None,
            local_cash=Decimal("9500"),
            broker_positions_json=None,
            local_positions_json={"symbol": "SPY", "quantity": "1"},
            mismatch_details_json={"syncType": "ORDER_STATUS_SYNC"},
            error_message=None,
            created_at=now,
        )
    )
    session.commit()


def test_paper_operations_endpoints_return_persisted_audit_rows(
    client, migrated_database: str
) -> None:
    session_factory = create_session_factory(migrated_database)
    with session_factory() as session:
        experiment_id = _create_paper_experiment(session, status=ExperimentStatus.RUNNING)
        _add_paper_artifacts(session, experiment_id)

    orders = client.get(f"/api/v1/experiments/{experiment_id}/orders")
    trades = client.get(f"/api/v1/experiments/{experiment_id}/trades")
    sync_logs = client.get(f"/api/v1/experiments/{experiment_id}/broker-sync-logs")

    assert orders.status_code == 200
    assert orders.json()["items"][0]["brokerOrderId"] == "paper-order-1"
    assert trades.status_code == 200
    assert trades.json()["items"][0]["price"] == 500.0
    assert sync_logs.status_code == 200
    assert sync_logs.json()["items"][0]["syncStatus"] == "SUCCESS"


def test_paper_status_explains_disabled_scheduler(
    monkeypatch, migrated_database: str
) -> None:
    monkeypatch.setenv("PAPER_TRADING_SCHEDULER_ENABLED", "false")
    get_settings.cache_clear()
    session_factory = create_session_factory(migrated_database)
    with session_factory() as session:
        experiment_id = _create_paper_experiment(session, status=ExperimentStatus.RUNNING)

    with TestClient(create_app()) as client:
        response = client.get(f"/api/v1/experiments/{experiment_id}/paper-status")

    assert response.status_code == 200
    body = response.json()
    assert body["supportedByPaperScheduler"] is True
    assert body["paperTradingSchedulerEnabled"] is False
    assert body["reasonCode"] == "PAPER_TRADING_SCHEDULER_DISABLED"
    get_settings.cache_clear()


def test_paper_status_explains_disabled_smoke_test_mode(
    monkeypatch, migrated_database: str
) -> None:
    monkeypatch.setenv("PAPER_TRADING_TEST_MODE_ENABLED", "false")
    get_settings.cache_clear()
    session_factory = create_session_factory(migrated_database)
    with session_factory() as session:
        experiment_id = _create_paper_experiment(
            session,
            status=ExperimentStatus.RUNNING,
            strategy_type=StrategyType.PAPER_TRADING_SMOKE_TEST,
            trading_frequency=TradingFrequency.TEST_1_MIN,
        )

    with TestClient(create_app()) as client:
        response = client.get(f"/api/v1/experiments/{experiment_id}/paper-status")

    assert response.status_code == 200
    assert response.json()["reasonCode"] == "PAPER_TRADING_TEST_MODE_DISABLED"
    get_settings.cache_clear()


def test_paper_status_supports_orb_and_exposes_operational_metadata(
    monkeypatch, migrated_database: str
) -> None:
    monkeypatch.setenv("PAPER_TRADING_SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("ALPACA_PAPER_TRADING_ENABLED", "true")
    monkeypatch.setenv("ALPACA_API_KEY_ID", "test-key")
    monkeypatch.setenv("ALPACA_API_SECRET_KEY", "test-secret")
    get_settings.cache_clear()
    session_factory = create_session_factory(migrated_database)
    with session_factory() as session:
        experiment_id = _create_paper_experiment(
            session,
            status=ExperimentStatus.RUNNING,
            strategy_type=StrategyType.OPENING_RANGE_BREAKOUT,
            trading_frequency=TradingFrequency.INTRADAY_5_MIN,
        )

    with TestClient(create_app()) as client:
        response = client.get(f"/api/v1/experiments/{experiment_id}/paper-status")

    assert response.status_code == 200
    body = response.json()
    assert body["supportedByPaperScheduler"] is True
    assert body["operationalMetadata"]["strategy"] == "OPENING_RANGE_BREAKOUT"
    assert "nextDueBarTimestamp" in body["operationalMetadata"]
    get_settings.cache_clear()


def test_paper_status_supports_orb_for_supported_tech_asset(
    monkeypatch,
    migrated_database: str,
) -> None:
    monkeypatch.setenv("PAPER_TRADING_SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("ALPACA_PAPER_TRADING_ENABLED", "true")
    monkeypatch.setenv("ALPACA_API_KEY_ID", "test-key")
    monkeypatch.setenv("ALPACA_API_SECRET_KEY", "test-secret")
    get_settings.cache_clear()
    session_factory = create_session_factory(migrated_database)
    with session_factory() as session:
        experiment_id = _create_paper_experiment(
            session,
            status=ExperimentStatus.RUNNING,
            strategy_type=StrategyType.OPENING_RANGE_BREAKOUT,
            trading_frequency=TradingFrequency.INTRADAY_5_MIN,
        )
        experiment = session.get(ExperimentModel, experiment_id)
        assert experiment is not None
        experiment.asset_symbol = "AAPL"
        session.commit()

    with TestClient(create_app()) as client:
        response = client.get(f"/api/v1/experiments/{experiment_id}/paper-status")

    assert response.status_code == 200
    body = response.json()
    assert body["supportedByPaperScheduler"] is True
    assert body["assetSymbol"] == "AAPL"
    get_settings.cache_clear()


def test_paper_status_supports_hourly_agentic_ai(
    monkeypatch, migrated_database: str
) -> None:
    monkeypatch.setenv("PAPER_TRADING_SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("ALPACA_PAPER_TRADING_ENABLED", "true")
    monkeypatch.setenv("ALPACA_API_KEY_ID", "test-key")
    monkeypatch.setenv("ALPACA_API_SECRET_KEY", "test-secret")
    get_settings.cache_clear()
    session_factory = create_session_factory(migrated_database)
    with session_factory() as session:
        experiment_id = _create_paper_experiment(
            session,
            status=ExperimentStatus.RUNNING,
            strategy_type=StrategyType.AGENTIC_AI,
            trading_frequency=TradingFrequency.HOURLY,
        )
        config = session.scalar(
            select(StrategyConfigModel).where(
                StrategyConfigModel.experiment_id == experiment_id
            )
        )
        assert config is not None
        config.agent_mode = AgentMode.PIPELINE
        session.commit()

    with TestClient(create_app()) as client:
        response = client.get(f"/api/v1/experiments/{experiment_id}/paper-status")

    assert response.status_code == 200
    body = response.json()
    assert body["supportedByPaperScheduler"] is True
    assert body["tradingFrequency"] == "HOURLY"
    assert body["operationalMetadata"]["strategy"] == "AGENTIC_AI"
    assert body["operationalMetadata"]["barInterval"] == "1Hour"
    get_settings.cache_clear()


def test_paper_operations_missing_experiment_returns_404(client) -> None:
    response = client.get("/api/v1/experiments/9999/orders")

    assert response.status_code == 404
    assert response.json()["errorCode"] == "EXPERIMENT_NOT_FOUND"
