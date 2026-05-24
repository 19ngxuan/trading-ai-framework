from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import InvalidExperimentConfigurationAppError
from app.domain.enums import (
    AgentMode,
    AgentStepName,
    DecisionSourceType,
    ExecutionStepStatus,
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    FinalAction,
    StrategyType,
    TradeAction,
    TradingFrequency,
)
from app.modules.execution.paper_step_runner import PaperTradingStepRunner
from app.modules.execution.step_runner import HistoricalStepRunner
from app.persistence.database import create_session_factory
from app.persistence.models import (
    AgentDecisionLogModel,
    ExecutionStepModel,
    ExperimentModel,
    OrderModel,
    PortfolioModel,
    RiskCheckModel,
    StrategyConfigModel,
    TradeModel,
    TradingDecisionModel,
)


class BrokerMustNotBeCalled:
    def place_order(self, **kwargs):
        raise AssertionError("Pipeline paper trading must not call broker.")

    def get_order_status(self, broker_order_id: str):
        raise AssertionError("Pipeline paper trading must not call broker.")

    def get_account_state(self):
        raise AssertionError("Pipeline paper trading must not call broker.")

    def get_positions(self):
        raise AssertionError("Pipeline paper trading must not call broker.")


def _pipeline_parameters(
    *, action: str = "BUY", verdict: str = "APPROVE", confidence: float = 0.8
) -> dict:
    return {
        "fakePipeline": {
            "marketAnalystOutput": {
                "marketBias": "BULLISH",
                "confidence": 0.8,
                "rationale": "Bullish context.",
            },
            "tradingDecisionOutput": {
                "action": action,
                "confidence": confidence,
                "rationale": "Pipeline proposal.",
            },
            "riskManagerOutput": {
                "verdict": verdict,
                "confidence": 0.9,
                "rationale": "Agent-level verdict.",
            },
        }
    }


def _create_pipeline_experiment(
    session: Session,
    *,
    parameters_json: dict,
    confidence_threshold: Decimal | None = None,
    mode: ExperimentMode = ExperimentMode.HISTORICAL_SIMULATION,
) -> int:
    now = datetime(2026, 1, 1, 12, 0, 0)
    experiment = ExperimentModel(
        name="M11 pipeline",
        mode=mode,
        strategy_type=StrategyType.AGENTIC_AI,
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
            strategy_type=StrategyType.AGENTIC_AI,
            strategy_version="agentic-ai-pipeline-v1",
            moving_average_window=None,
            position_sizing_type="ALL_IN",
            agent_mode=AgentMode.PIPELINE,
            model_name="deterministic-fake-pipeline",
            confidence_threshold=confidence_threshold,
            parameters_json=parameters_json,
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


def test_pipeline_manual_step_persists_three_logs_and_single_decision(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_pipeline_experiment(
            session, parameters_json=_pipeline_parameters()
        )

    result = HistoricalStepRunner(session_factory=session_factory).run_next_step(
        experiment_id
    )

    assert result.status is ExecutionStepStatus.COMPLETED
    with session_factory() as session:
        assert _count(session, AgentDecisionLogModel, experiment_id) == 3
        assert _count(session, TradingDecisionModel, experiment_id) == 1
        assert _count(session, RiskCheckModel, experiment_id) == 1
        assert _count(session, OrderModel, experiment_id) == 1
        assert _count(session, TradeModel, experiment_id) == 1

        logs = list(
            session.scalars(
                select(AgentDecisionLogModel)
                .where(AgentDecisionLogModel.experiment_id == experiment_id)
                .order_by(AgentDecisionLogModel.id)
            )
        )
        assert [log.agent_step_name for log in logs] == [
            AgentStepName.MARKET_ANALYST,
            AgentStepName.TRADING_DECISION,
            AgentStepName.RISK_MANAGER,
        ]
        assert [log.parsed_output_json["pipelineStage"] for log in logs] == [
            AgentStepName.MARKET_ANALYST.value,
            AgentStepName.TRADING_DECISION.value,
            AgentStepName.RISK_MANAGER.value,
        ]

        decision = session.scalar(
            select(TradingDecisionModel).where(
                TradingDecisionModel.experiment_id == experiment_id
            )
        )
        risk_check = session.scalar(
            select(RiskCheckModel).where(RiskCheckModel.experiment_id == experiment_id)
        )
        assert decision is not None
        assert risk_check is not None
        assert decision.source_type is DecisionSourceType.AGENT
        assert decision.action is TradeAction.BUY
        assert decision.raw_decision_json["originalAction"] == "BUY"
        assert decision.raw_decision_json["finalAction"] == "BUY"
        assert decision.raw_decision_json["pipelineStages"] == [
            AgentStepName.MARKET_ANALYST.value,
            AgentStepName.TRADING_DECISION.value,
            AgentStepName.RISK_MANAGER.value,
        ]
        assert risk_check.trading_decision_id == decision.id
        assert risk_check.final_action is FinalAction.BUY
        assert {log.trading_decision_id for log in logs} == {decision.id}


def test_pipeline_rejected_proposal_creates_no_order_or_trade(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_pipeline_experiment(
            session,
            parameters_json=_pipeline_parameters(action="BUY", verdict="REJECT"),
        )

    HistoricalStepRunner(session_factory=session_factory).run_next_step(experiment_id)

    with session_factory() as session:
        decision = session.scalar(
            select(TradingDecisionModel).where(
                TradingDecisionModel.experiment_id == experiment_id
            )
        )
        risk_check = session.scalar(
            select(RiskCheckModel).where(RiskCheckModel.experiment_id == experiment_id)
        )
        assert decision is not None
        assert risk_check is not None
        assert decision.action is TradeAction.HOLD
        assert decision.raw_decision_json["originalAction"] == "BUY"
        assert decision.raw_decision_json["finalAction"] == "HOLD"
        assert decision.raw_decision_json["fallbackReason"] == (
            "AGENT_RISK_MANAGER_REJECTED"
        )
        assert risk_check.final_action is FinalAction.HOLD
        assert _count(session, OrderModel, experiment_id) == 0
        assert _count(session, TradeModel, experiment_id) == 0


def test_pipeline_low_confidence_creates_hold_before_risk_check(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_pipeline_experiment(
            session,
            confidence_threshold=Decimal("0.7500"),
            parameters_json=_pipeline_parameters(confidence=0.2),
        )

    HistoricalStepRunner(session_factory=session_factory).run_next_step(experiment_id)

    with session_factory() as session:
        decision = session.scalar(
            select(TradingDecisionModel).where(
                TradingDecisionModel.experiment_id == experiment_id
            )
        )
        assert decision is not None
        assert decision.action is TradeAction.HOLD
        assert decision.raw_decision_json["confidenceThresholdApplied"] is True
        assert _count(session, OrderModel, experiment_id) == 0


def test_pipeline_sell_without_position_is_stopped_by_risk_check(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_pipeline_experiment(
            session,
            parameters_json=_pipeline_parameters(action="SELL", verdict="APPROVE"),
        )

    HistoricalStepRunner(session_factory=session_factory).run_next_step(experiment_id)

    with session_factory() as session:
        decision = session.scalar(
            select(TradingDecisionModel).where(
                TradingDecisionModel.experiment_id == experiment_id
            )
        )
        risk_check = session.scalar(
            select(RiskCheckModel).where(RiskCheckModel.experiment_id == experiment_id)
        )
        assert decision is not None
        assert risk_check is not None
        assert decision.action is TradeAction.SELL
        assert risk_check.final_action is FinalAction.HOLD
        assert risk_check.rules_triggered_json["reason"] == "NO_POSITION_TO_SELL"
        assert (
            risk_check.rules_triggered_json["positionSizing"]["sizingReason"]
            == "NO_POSITION_TO_SELL"
        )
        assert _count(session, OrderModel, experiment_id) == 0
        assert _count(session, TradeModel, experiment_id) == 0


def test_pipeline_paper_trading_is_rejected_without_broker_call(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_pipeline_experiment(
            session,
            mode=ExperimentMode.PAPER_TRADING,
            parameters_json=_pipeline_parameters(),
        )

    runner = PaperTradingStepRunner(
        session_factory=session_factory,
        broker_adapter=BrokerMustNotBeCalled(),
    )
    try:
        runner.run_next_step(experiment_id)
    except InvalidExperimentConfigurationAppError:
        pass
    else:
        raise AssertionError("Pipeline paper trading should be rejected.")

    with session_factory() as session:
        assert _count(session, ExecutionStepModel, experiment_id) == 0
        assert _count(session, OrderModel, experiment_id) == 0
        assert _count(session, TradeModel, experiment_id) == 0
