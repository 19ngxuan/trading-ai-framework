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
)
from app.modules.agents.fake_pipeline_provider import FakePipelineProvider
from app.modules.agents.pipeline_agent import AgentDecisionPipeline
from app.modules.broker.broker_adapter import BrokerAccountState, BrokerOrderResult, BrokerPosition
from app.modules.execution.paper_step_runner import PaperTradingStepRunner
from app.modules.execution.step_runner import HistoricalStepRunner
from app.modules.strategies.agentic_ai_strategy import AgenticAIStrategy
from app.domain.enums import OrderSide, OrderType
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


class FakeBrokerAdapter:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def place_order(
        self,
        *,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType,
        client_order_id: str,
    ) -> BrokerOrderResult:
        self.calls.append(
            {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "orderType": order_type,
                "clientOrderId": client_order_id,
            }
        )
        return BrokerOrderResult(
            broker_order_id="pipeline-paper-filled",
            status="filled",
            symbol=symbol,
            side=side,
            quantity=quantity,
            filled_quantity=quantity,
            average_fill_price=Decimal("100.00"),
            submitted_at=datetime(2026, 1, 2, 12, 0, 0),
            filled_at=datetime(2026, 1, 2, 12, 1, 0),
            raw={"status": "filled"},
        )

    def get_order_status(self, broker_order_id: str) -> BrokerOrderResult:
        raise AssertionError("Order status polling is not expected in this test.")

    def get_account_state(self) -> BrokerAccountState:
        return BrokerAccountState(cash=None, status=None, raw={})

    def get_positions(self) -> list[BrokerPosition]:
        return []


def _pipeline_parameters() -> dict:
    return {
        "riskConfig": {"fallbackAction": "HOLD"},
        "fakePipeline": {
            "marketAnalystOutput": {
                "marketBias": "BULLISH",
                "confidence": 0.8,
                "rationale": "Bullish context.",
            },
            "tradingDecisionOutput": {
                "action": "BUY",
                "confidence": 0.8,
                "rationale": "Pipeline proposal.",
            },
            "riskManagerOutput": {
                "verdict": "APPROVE",
                "confidence": 0.9,
                "rationale": "Agent-level verdict.",
            },
        },
    }


def _create_pipeline_experiment(
    session: Session,
    *,
    mode: ExperimentMode,
) -> int:
    now = datetime(2026, 1, 1, 12, 0, 0)
    experiment = ExperimentModel(
        name="Legacy Agentic AI pipeline",
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
            moving_average_window=None,
            agent_mode=AgentMode.PIPELINE,
            model_name="deterministic-fake-pipeline",
            confidence_threshold=None,
            parameters_json=_pipeline_parameters(),
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
        AgentDecisionLogModel,
        TradingDecisionModel,
        RiskCheckModel,
        OrderModel,
        TradeModel,
    ):
        assert _count(session, model, experiment_id) == 0


def test_pipeline_historical_step_is_rejected_before_artifacts(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_pipeline_experiment(
            session,
            mode=ExperimentMode.HISTORICAL_SIMULATION,
        )

    try:
        HistoricalStepRunner(session_factory=session_factory).run_next_step(
            experiment_id
        )
    except InvalidExperimentConfigurationAppError as exc:
        assert exc.details["strategyType"] == StrategyType.AGENTIC_AI.value
    else:
        raise AssertionError("Historical Agentic AI pipeline should be rejected.")

    with session_factory() as session:
        _assert_no_execution_artifacts(session, experiment_id)


def test_pipeline_paper_trading_persists_artifacts_and_uses_broker_path(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_pipeline_experiment(
            session,
            mode=ExperimentMode.PAPER_TRADING,
        )

    broker_adapter = FakeBrokerAdapter()
    runner = PaperTradingStepRunner(
        session_factory=session_factory,
        broker_adapter=broker_adapter,
        agent_strategy=AgenticAIStrategy(
            pipeline=AgentDecisionPipeline(provider=FakePipelineProvider())
        ),
    )
    result = runner.run_next_step(experiment_id)

    assert result.status.value == "COMPLETED"

    with session_factory() as session:
        assert _count(session, AgentDecisionLogModel, experiment_id) == 3
        assert _count(session, TradingDecisionModel, experiment_id) == 1
        assert _count(session, RiskCheckModel, experiment_id) == 1
        assert _count(session, OrderModel, experiment_id) == 1
        assert _count(session, TradeModel, experiment_id) == 1
    assert len(broker_adapter.calls) == 1
