from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.enums import (
    AgentMode,
    AgentStepName,
    DecisionSourceType,
    ExecutionStepStatus,
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    ParsingStatus,
    PrimaryDriver,
    StrategyType,
    TradeAction,
    TradeIntent,
    TradingFrequency,
    TriggerType,
)
from app.persistence.database import create_session_factory
from app.persistence.models import (
    AgentDecisionLogModel,
    ExecutionStepModel,
    ExperimentModel,
    MarketDataSnapshotModel,
    PortfolioModel,
    StrategyConfigModel,
    TradingDecisionModel,
)


def _create_agent_experiment(session: Session) -> int:
    now = datetime(2026, 1, 1, 12, 0, 0)
    experiment = ExperimentModel(
        name="Agent Audit",
        mode=ExperimentMode.PAPER_TRADING,
        strategy_type=StrategyType.AGENTIC_AI,
        asset_symbol="SPY",
        status=ExperimentStatus.RUNNING,
        initial_capital=Decimal("10000.0000"),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
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
            strategy_type=StrategyType.AGENTIC_AI,
            moving_average_window=None,
            agent_mode=AgentMode.PIPELINE,
            model_name="meta-llama/Llama-3.3-70B-Instruct",
            confidence_threshold=Decimal("0.7000"),
            parameters_json={},
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


def _add_agent_log(session: Session, experiment_id: int) -> None:
    now = datetime(2026, 1, 1, 15, 55, 0)
    step = ExecutionStepModel(
        experiment_id=experiment_id,
        scheduled_for=now,
        started_at=now,
        completed_at=now,
        status=ExecutionStepStatus.COMPLETED,
        trigger_type=TriggerType.EVENT,
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
        source_type=DecisionSourceType.AGENT,
        source_name="multi-agent-v2",
        action=TradeAction.BUY,
        symbol="SPY",
        suggested_quantity=None,
        suggested_notional=None,
        confidence=Decimal("0.8600"),
        trade_intent=TradeIntent.OPEN_LONG,
        target_exposure_pct=Decimal("0.250000"),
        primary_driver=PrimaryDriver.EVENT_RISK,
        new_information=True,
        reason="Event changed the trading thesis.",
        raw_decision_json={"agentVersion": "MULTI_AGENT_V2_TRADING"},
        created_at=now,
    )
    session.add(decision)
    session.flush()
    session.add(
        AgentDecisionLogModel(
            execution_step_id=step.id,
            experiment_id=experiment_id,
            trading_decision_id=decision.id,
            agent_mode=AgentMode.PIPELINE,
            agent_step_name=AgentStepName.TRADING_DECISION,
            agent_name="TradingDecisionAgent",
            prompt_version="agent-v2",
            model_name="meta-llama/Llama-3.3-70B-Instruct",
            model_version=None,
            input_json={
                "eventContext": {
                    "headline": "SPY event",
                    "eventType": "GENERAL_MARKET_NEWS",
                    "severity": "MEDIUM",
                }
            },
            prompt_text="prompt",
            raw_output_text='{"action":"BUY"}',
            parsed_output_json={
                "action": "BUY",
                "tradeIntent": "OPEN_LONG",
                "targetExposurePct": 0.25,
                "confidence": 0.86,
                "primaryDriver": "EVENT_RISK",
                "newInformation": True,
                "rationale": "Event changed the trading thesis.",
            },
            parsing_status=ParsingStatus.SUCCESS,
            repair_prompt_text=None,
            repair_raw_output_text=None,
            created_at=now,
        )
    )
    session.commit()


def test_agent_decision_logs_endpoint_returns_persisted_audit_rows(
    client,
    migrated_database: str,
) -> None:
    session_factory = create_session_factory(migrated_database)
    with session_factory() as session:
        experiment_id = _create_agent_experiment(session)
        _add_agent_log(session, experiment_id)

    response = client.get(f"/api/v1/experiments/{experiment_id}/agent-decision-logs")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["agentMode"] == "PIPELINE"
    assert item["agentStepName"] == "TRADING_DECISION"
    assert item["triggerType"] == "EVENT"
    assert item["executionStepSequenceNumber"] == 1
    assert item["parsedOutputJson"]["tradeIntent"] == "OPEN_LONG"
    assert item["inputJson"]["eventContext"]["headline"] == "SPY event"


def test_agent_decision_logs_endpoint_returns_404_for_missing_experiment(
    client,
) -> None:
    response = client.get("/api/v1/experiments/999/agent-decision-logs")

    assert response.status_code == 404
    assert response.json()["errorCode"] == "EXPERIMENT_NOT_FOUND"
