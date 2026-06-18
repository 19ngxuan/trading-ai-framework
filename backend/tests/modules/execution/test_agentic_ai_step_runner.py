from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import InvalidExperimentConfigurationAppError
from app.domain.enums import (
    AgentMode,
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    StrategyType,
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
    OrderModel,
    PortfolioModel,
    RiskCheckModel,
    StrategyConfigModel,
    TradeModel,
    TradingDecisionModel,
)


def _create_historical_agentic_experiment(
    session: Session,
    *,
    agent_mode: AgentMode = AgentMode.SINGLE_AGENT,
) -> int:
    now = datetime(2026, 1, 1, 12, 0, 0)
    experiment = ExperimentModel(
        name="Legacy historical Agentic AI",
        mode=ExperimentMode.HISTORICAL_SIMULATION,
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
            moving_average_window=None,
            agent_mode=agent_mode,
            model_name="deterministic-fake-agent",
            confidence_threshold=None,
            parameters_json={
                "riskConfig": {"fallbackAction": "HOLD"},
                "fakeAgent": {
                    "output": {
                        "action": "BUY",
                        "confidence": 0.9,
                        "rationale": "Historical Agentic AI is no longer supported.",
                    }
                },
            },
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


def _assert_no_execution_artifacts(session: Session, experiment_id: int) -> None:
    for model in (
        ExecutionStepModel,
        MarketDataSnapshotModel,
        AgentDecisionLogModel,
        TradingDecisionModel,
        RiskCheckModel,
        OrderModel,
        TradeModel,
    ):
        assert _count(session, model, experiment_id) == 0


def test_historical_agentic_ai_manual_step_is_rejected_before_artifacts(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_historical_agentic_experiment(session)

    try:
        HistoricalStepRunner(session_factory=session_factory).run_next_step(
            experiment_id
        )
    except InvalidExperimentConfigurationAppError as exc:
        assert exc.details["strategyType"] == StrategyType.AGENTIC_AI.value
    else:
        raise AssertionError("Historical Agentic AI should be rejected.")

    with session_factory() as session:
        _assert_no_execution_artifacts(session, experiment_id)


def test_historical_agentic_ai_scheduled_step_is_rejected_before_artifacts(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_historical_agentic_experiment(session)

    try:
        HistoricalStepRunner(session_factory=session_factory).run_next_step(
            experiment_id,
            trigger_type=TriggerType.SCHEDULED,
        )
    except InvalidExperimentConfigurationAppError as exc:
        assert exc.details["strategyType"] == StrategyType.AGENTIC_AI.value
    else:
        raise AssertionError("Scheduled historical Agentic AI should be rejected.")

    with session_factory() as session:
        _assert_no_execution_artifacts(session, experiment_id)
