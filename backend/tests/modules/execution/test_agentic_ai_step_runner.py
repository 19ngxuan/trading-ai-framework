from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import InvalidExperimentConfigurationAppError
from app.domain.enums import (
    AgentMode,
    DecisionSourceType,
    ExecutionStepStatus,
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    FinalAction,
    ParsingStatus,
    StrategyType,
    TradeAction,
    TradingFrequency,
    TriggerType,
)
from app.modules.execution.step_runner import HistoricalStepRunner
from app.persistence.database import create_session_factory
from app.persistence.models import (
    AgentDecisionLogModel,
    ExecutionStepModel,
    ExperimentModel,
    MarketDataSnapshotModel,
    MetricSnapshotModel,
    OrderModel,
    PortfolioModel,
    PortfolioSnapshotModel,
    RiskCheckModel,
    StrategyConfigModel,
    TradeModel,
    TradingDecisionModel,
)
from app.modules.execution.paper_step_runner import PaperTradingStepRunner


class BrokerMustNotBeCalled:
    def place_order(self, **kwargs):
        raise AssertionError("Agentic AI paper trading must not call broker.")

    def get_order_status(self, broker_order_id: str):
        raise AssertionError("Agentic AI paper trading must not call broker.")

    def get_account_state(self):
        raise AssertionError("Agentic AI paper trading must not call broker.")

    def get_positions(self):
        raise AssertionError("Agentic AI paper trading must not call broker.")


def _create_agentic_experiment(
    session: Session,
    *,
    parameters_json: dict,
    confidence_threshold: Decimal | None = None,
    initial_capital: Decimal = Decimal("10000.0000"),
    mode: ExperimentMode = ExperimentMode.HISTORICAL_SIMULATION,
    trading_frequency: TradingFrequency = TradingFrequency.DAILY,
    asset_symbol: str = "SPY",
    position_sizing_type: str = "ALL_IN",
    position_sizing_value: Decimal | None = None,
) -> int:
    now = datetime(2026, 1, 1, 12, 0, 0)
    experiment = ExperimentModel(
        name="M10 agentic AI",
        mode=mode,
        strategy_type=StrategyType.AGENTIC_AI,
        asset_symbol=asset_symbol,
        status=ExperimentStatus.RUNNING,
        initial_capital=initial_capital,
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 5),
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
            strategy_type=StrategyType.AGENTIC_AI,
            strategy_version="agentic-ai-v1",
            moving_average_window=None,
            position_sizing_type=position_sizing_type,
            agent_mode=AgentMode.SINGLE_AGENT,
            model_name="deterministic-fake-agent",
            confidence_threshold=confidence_threshold,
            parameters_json={
                **parameters_json,
                **(
                    {"positionSizingValue": float(position_sizing_value)}
                    if position_sizing_value is not None
                    else {}
                ),
            },
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


def test_agentic_ai_manual_step_persists_audit_chain_and_buy(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_agentic_experiment(
            session,
            parameters_json={
                "fakeAgent": {
                    "output": {
                        "action": "BUY",
                        "confidence": 0.9,
                        "rationale": "Deterministic buy.",
                    }
                }
            },
        )

    result = HistoricalStepRunner(session_factory=session_factory).run_next_step(
        experiment_id
    )

    assert result.execution_step_id is not None
    assert result.status is ExecutionStepStatus.COMPLETED
    with session_factory() as session:
        assert _count(session, ExecutionStepModel, experiment_id) == 1
        assert _count(session, MarketDataSnapshotModel, experiment_id) == 1
        assert _count(session, AgentDecisionLogModel, experiment_id) == 1
        assert _count(session, TradingDecisionModel, experiment_id) == 1
        assert _count(session, RiskCheckModel, experiment_id) == 1
        assert _count(session, PortfolioSnapshotModel, experiment_id) == 1
        assert _count(session, MetricSnapshotModel, experiment_id) == 1
        assert _count(session, OrderModel, experiment_id) == 1
        assert _count(session, TradeModel, experiment_id) == 1

        decision = session.scalar(
            select(TradingDecisionModel).where(
                TradingDecisionModel.experiment_id == experiment_id
            )
        )
        risk_check = session.scalar(
            select(RiskCheckModel).where(RiskCheckModel.experiment_id == experiment_id)
        )
        agent_log = session.scalar(
            select(AgentDecisionLogModel).where(
                AgentDecisionLogModel.experiment_id == experiment_id
            )
        )
        assert decision is not None
        assert risk_check is not None
        assert agent_log is not None
        assert decision.source_type is DecisionSourceType.AGENT
        assert decision.action is TradeAction.BUY
        assert risk_check.trading_decision_id == decision.id
        assert risk_check.final_action is FinalAction.BUY
        assert agent_log.trading_decision_id == decision.id
        assert agent_log.parsing_status is ParsingStatus.SUCCESS


def test_agentic_ai_buy_uses_configured_position_sizing(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_agentic_experiment(
            session,
            parameters_json={
                "fakeAgent": {
                    "output": {
                        "action": "BUY",
                        "confidence": 0.9,
                        "rationale": "Deterministic buy.",
                    }
                }
            },
            position_sizing_type="FIXED_QUANTITY",
            position_sizing_value=Decimal("3"),
        )

    HistoricalStepRunner(session_factory=session_factory).run_next_step(experiment_id)

    with session_factory() as session:
        risk_check = session.scalar(
            select(RiskCheckModel).where(RiskCheckModel.experiment_id == experiment_id)
        )
        trade = session.scalar(
            select(TradeModel).where(TradeModel.experiment_id == experiment_id)
        )
        assert risk_check is not None
        assert trade is not None
        assert risk_check.final_quantity == Decimal("3.00000000")
        assert trade.quantity == Decimal("3.00000000")
        assert (
            risk_check.rules_triggered_json["positionSizing"]["sizingReason"]
            == "FIXED_QUANTITY"
        )


def test_agentic_ai_invalid_output_repairs_to_hold(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_agentic_experiment(
            session,
            parameters_json={
                "fakeAgent": {
                    "output": "not json",
                    "repairOutput": {
                        "action": "HOLD",
                        "confidence": 0.6,
                        "rationale": "Repaired hold.",
                    },
                }
            },
        )

    HistoricalStepRunner(session_factory=session_factory).run_next_step(experiment_id)

    with session_factory() as session:
        decision = session.scalar(
            select(TradingDecisionModel).where(
                TradingDecisionModel.experiment_id == experiment_id
            )
        )
        agent_log = session.scalar(
            select(AgentDecisionLogModel).where(
                AgentDecisionLogModel.experiment_id == experiment_id
            )
        )
        assert decision is not None
        assert agent_log is not None
        assert decision.action is TradeAction.HOLD
        assert agent_log.parsing_status is ParsingStatus.REPAIRED
        assert agent_log.repair_prompt_text is not None
        assert agent_log.repair_raw_output_text is not None
        assert _count(session, OrderModel, experiment_id) == 0
        assert _count(session, TradeModel, experiment_id) == 0


def test_agentic_ai_failed_repair_falls_back_to_hold(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_agentic_experiment(
            session,
            parameters_json={
                "fakeAgent": {
                    "output": "not json",
                    "repairOutput": "still not json",
                }
            },
        )

    HistoricalStepRunner(session_factory=session_factory).run_next_step(experiment_id)

    with session_factory() as session:
        decision = session.scalar(
            select(TradingDecisionModel).where(
                TradingDecisionModel.experiment_id == experiment_id
            )
        )
        agent_log = session.scalar(
            select(AgentDecisionLogModel).where(
                AgentDecisionLogModel.experiment_id == experiment_id
            )
        )
        assert decision is not None
        assert agent_log is not None
        assert decision.action is TradeAction.HOLD
        assert decision.confidence == Decimal("0.0000")
        assert agent_log.parsing_status is ParsingStatus.FAILED
        assert agent_log.parsed_output_json["fallbackUsed"] is True


def test_agentic_ai_low_confidence_converts_to_hold(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_agentic_experiment(
            session,
            confidence_threshold=Decimal("0.7500"),
            parameters_json={
                "fakeAgent": {
                    "output": {
                        "action": "BUY",
                        "confidence": 0.4,
                        "rationale": "Weak buy.",
                    }
                }
            },
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
        agent_log = session.scalar(
            select(AgentDecisionLogModel).where(
                AgentDecisionLogModel.experiment_id == experiment_id
            )
        )
        assert decision is not None
        assert risk_check is not None
        assert agent_log is not None
        assert decision.action is TradeAction.HOLD
        assert risk_check.final_action is FinalAction.HOLD
        assert agent_log.parsed_output_json["confidenceThresholdApplied"] is True
        assert _count(session, OrderModel, experiment_id) == 0
        assert _count(session, TradeModel, experiment_id) == 0


def test_agentic_ai_sell_never_shorts(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_agentic_experiment(
            session,
            parameters_json={
                "fakeAgent": {
                    "output": {
                        "action": "SELL",
                        "confidence": 0.9,
                        "rationale": "Try to sell without position.",
                    }
                }
            },
        )

    HistoricalStepRunner(session_factory=session_factory).run_next_step(experiment_id)

    with session_factory() as session:
        risk_check = session.scalar(
            select(RiskCheckModel).where(RiskCheckModel.experiment_id == experiment_id)
        )
        portfolio = session.scalar(
            select(PortfolioModel).where(PortfolioModel.experiment_id == experiment_id)
        )
        assert risk_check is not None
        assert portfolio is not None
        assert risk_check.final_action is FinalAction.HOLD
        assert risk_check.rules_triggered_json["reason"] == "NO_POSITION_TO_SELL"
        assert (
            risk_check.rules_triggered_json["positionSizing"]["sizingReason"]
            == "NO_POSITION_TO_SELL"
        )
        assert portfolio.position_quantity == Decimal("0E-8")
        assert _count(session, OrderModel, experiment_id) == 0
        assert _count(session, TradeModel, experiment_id) == 0


def test_agentic_ai_paper_trading_is_rejected_without_broker_call(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_agentic_experiment(
            session,
            mode=ExperimentMode.PAPER_TRADING,
            parameters_json={
                "fakeAgent": {
                    "output": {
                        "action": "BUY",
                        "confidence": 0.9,
                        "rationale": "Paper agent is out of scope.",
                    }
                }
            },
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
        raise AssertionError("Agentic AI paper trading should be rejected.")

    with session_factory() as session:
        assert _count(session, ExecutionStepModel, experiment_id) == 0
        assert _count(session, OrderModel, experiment_id) == 0
        assert _count(session, TradeModel, experiment_id) == 0


def test_agentic_ai_scheduled_trigger_is_rejected_before_artifacts(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_agentic_experiment(
            session,
            parameters_json={
                "fakeAgent": {
                    "output": {
                        "action": "BUY",
                        "confidence": 0.9,
                        "rationale": "Scheduled agent is out of scope.",
                    }
                }
            },
        )

    try:
        HistoricalStepRunner(session_factory=session_factory).run_next_step(
            experiment_id, trigger_type=TriggerType.SCHEDULED
        )
    except InvalidExperimentConfigurationAppError as exc:
        assert exc.details["triggerType"] == TriggerType.SCHEDULED.value
    else:
        raise AssertionError("Scheduled Agentic AI execution should be rejected.")

    with session_factory() as session:
        assert _count(session, ExecutionStepModel, experiment_id) == 0
        assert _count(session, MarketDataSnapshotModel, experiment_id) == 0
        assert _count(session, AgentDecisionLogModel, experiment_id) == 0
        assert _count(session, TradingDecisionModel, experiment_id) == 0
        assert _count(session, RiskCheckModel, experiment_id) == 0
        assert _count(session, OrderModel, experiment_id) == 0
        assert _count(session, TradeModel, experiment_id) == 0
