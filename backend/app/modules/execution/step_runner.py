from dataclasses import dataclass
from datetime import datetime, time, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.errors import (
    ExperimentStepAlreadyRunningAppError,
    InvalidExperimentConfigurationAppError,
    InvalidStatusAppError,
    NotFoundAppError,
)
from app.domain.enums import (
    AgentMode,
    AgentStepName,
    DecisionSourceType,
    EventLevel,
    ExecutionStepStatus,
    ExperimentMode,
    ExperimentStatus,
    StrategyType,
    SystemEventType,
    TradingFrequency,
    TriggerType,
)
from app.modules.agents.types import AgentContext
from app.modules.execution.metrics import BasicMetricCalculator
from app.modules.execution.orchestrator import (
    HistoricalBuyAndHoldOrchestrator,
    HistoricalMovingAverageOrchestrator,
)
from app.modules.execution.risk import HistoricalSimulationRiskValidator
from app.modules.execution.simulation_provider import SimulationExecutionProvider
from app.modules.market_data.errors import (
    MarketDataProviderError,
    MarketDataUnavailableError,
)
from app.modules.market_data.factory import create_market_data_provider
from app.modules.market_data.provider import DailyBar, MarketDataProvider
from app.modules.strategies.agentic_ai_strategy import AgenticAIStrategy
from app.persistence.database import create_session_factory
from app.persistence.models import (
    AgentDecisionLogModel,
    ExecutionStepModel,
    MarketDataSnapshotModel,
    MetricSnapshotModel,
    PortfolioSnapshotModel,
    RiskCheckModel,
    SystemEventLogModel,
    TradingDecisionModel,
)
from app.persistence.repositories import (
    AgentDecisionLogRepository,
    ExecutionStepRepository,
    ExperimentRepository,
    MarketDataSnapshotRepository,
    MetricSnapshotRepository,
    PortfolioRepository,
    PortfolioSnapshotRepository,
    RiskCheckRepository,
    StrategyConfigRepository,
    SystemEventLogRepository,
    TradeRepository,
    TradingDecisionRepository,
)


@dataclass(frozen=True)
class StepRunResult:
    experiment_id: int
    execution_step_id: int | None
    status: ExecutionStepStatus | ExperimentStatus
    message: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _bar_timestamp(bar: DailyBar) -> datetime:
    return datetime.combine(bar.date, time.min)


class HistoricalStepRunner:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        market_data_provider: MarketDataProvider | None = None,
        csv_loader: MarketDataProvider | None = None,
        agent_strategy: AgenticAIStrategy | None = None,
    ) -> None:
        self.session_factory = session_factory or create_session_factory()
        self.market_data_provider = (
            market_data_provider
            or csv_loader
            or create_market_data_provider(get_settings())
        )
        self.agent_strategy = agent_strategy or AgenticAIStrategy()
        self.risk_validator = HistoricalSimulationRiskValidator()
        self.execution_provider = SimulationExecutionProvider()
        self.metric_calculator = BasicMetricCalculator()

    def run_next_step(
        self,
        experiment_id: int,
        trigger_type: TriggerType = TriggerType.MANUAL,
    ) -> StepRunResult:
        execution_step_id: int | None = None
        failure_step_id: int | None = None
        try:
            selected = self._select_bar_and_create_step(experiment_id, trigger_type)
            if selected is None:
                return StepRunResult(
                    experiment_id=experiment_id,
                    execution_step_id=None,
                    status=ExperimentStatus.COMPLETED,
                    message="Experiment completed; no remaining historical bars.",
                )

            bar, sequence_number, execution_step_id = selected
            failure_step_id = execution_step_id
            self._run_step_artifacts(experiment_id, bar, execution_step_id)
            failure_step_id = None
            if self._is_final_bar(experiment_id, sequence_number):
                self._complete_experiment(experiment_id)
            return StepRunResult(
                experiment_id=experiment_id,
                execution_step_id=execution_step_id,
                status=ExecutionStepStatus.COMPLETED,
                message="Manual execution step completed.",
            )
        except (
            ExperimentStepAlreadyRunningAppError,
            InvalidExperimentConfigurationAppError,
            InvalidStatusAppError,
            NotFoundAppError,
        ):
            raise
        except Exception as exc:
            self._persist_failure(experiment_id, failure_step_id, exc)
            raise

    def _select_bar_and_create_step(
        self, experiment_id: int, trigger_type: TriggerType
    ) -> tuple[DailyBar, int, int] | None:
        with self.session_factory() as session:
            experiment_repository = ExperimentRepository(session)
            execution_step_repository = ExecutionStepRepository(session)
            experiment = experiment_repository.get_by_id(experiment_id)
            if experiment is None:
                raise NotFoundAppError(
                    "Experiment was not found.",
                    details={"experimentId": experiment_id},
                )
            if experiment.status is not ExperimentStatus.RUNNING:
                raise InvalidStatusAppError(
                    "Experiment must be RUNNING to execute the next step.",
                    details={
                        "experimentId": experiment_id,
                        "status": experiment.status.value,
                    },
                )
            if (
                experiment.mode is not ExperimentMode.HISTORICAL_SIMULATION
                or experiment.strategy_type
                not in {
                    StrategyType.BUY_AND_HOLD,
                    StrategyType.MOVING_AVERAGE,
                    StrategyType.AGENTIC_AI,
                }
                or experiment.trading_frequency is not TradingFrequency.DAILY
                or experiment.asset_symbol != "SPY"
            ):
                raise InvalidExperimentConfigurationAppError(
                    "Manual stepping supports only daily historical SPY Buy-and-Hold, Moving Average, and Agentic AI experiments.",
                    details={
                        "experimentId": experiment_id,
                        "mode": experiment.mode.value,
                        "strategyType": experiment.strategy_type.value,
                        "tradingFrequency": experiment.trading_frequency.value,
                        "assetSymbol": experiment.asset_symbol,
                    },
                )

            lock_acquired = session.scalar(
                text("SELECT pg_try_advisory_xact_lock(:experiment_id)"),
                {"experiment_id": experiment_id},
            )
            if not lock_acquired:
                raise ExperimentStepAlreadyRunningAppError(
                    "Experiment already has a step in progress.",
                    details={"experimentId": experiment_id},
                )

            if execution_step_repository.has_running_step(experiment_id):
                raise ExperimentStepAlreadyRunningAppError(
                    "Experiment already has a step in progress.",
                    details={"experimentId": experiment_id},
                )

            bars = self.market_data_provider.load_range(
                experiment.start_date, experiment.end_date
            )
            next_index = execution_step_repository.max_sequence_number(experiment_id)
            if next_index >= len(bars):
                self._mark_completed_in_session(session, experiment_id)
                session.commit()
                return None

            bar = bars[next_index]
            sequence_number = next_index + 1
            now = _utcnow()
            execution_step = execution_step_repository.add(
                ExecutionStepModel(
                    experiment_id=experiment_id,
                    scheduled_for=_bar_timestamp(bar),
                    started_at=now,
                    completed_at=None,
                    status=ExecutionStepStatus.RUNNING,
                    trigger_type=trigger_type,
                    sequence_number=sequence_number,
                    error_message=None,
                    created_at=now,
                )
            )
            session.flush()
            execution_step_id = execution_step.id
            session.commit()
            return bar, sequence_number, execution_step_id

    def _run_step_artifacts(
        self, experiment_id: int, bar: DailyBar, execution_step_id: int
    ) -> None:
        strategy_type = self._strategy_type(experiment_id)
        if strategy_type is StrategyType.BUY_AND_HOLD:
            HistoricalBuyAndHoldOrchestrator(
                session_factory=self.session_factory,
                market_data_provider=self.market_data_provider,
            )._run_step(experiment_id, bar, execution_step_id)
            return
        if strategy_type is StrategyType.AGENTIC_AI:
            self._run_agentic_ai_step(experiment_id, bar, execution_step_id)
            return

        orchestrator = HistoricalMovingAverageOrchestrator(
            session_factory=self.session_factory,
            market_data_provider=self.market_data_provider,
        )
        prices = self._prices_through_bar(experiment_id, bar)
        window = orchestrator._moving_average_window(experiment_id)
        moving_average = orchestrator._moving_average(prices, window)
        orchestrator._run_step(
            experiment_id,
            bar,
            execution_step_id,
            moving_average,
            window,
        )

    def _strategy_type(self, experiment_id: int) -> StrategyType:
        with self.session_factory() as session:
            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            if experiment is None:
                raise NotFoundAppError(
                    "Experiment was not found.",
                    details={"experimentId": experiment_id},
                )
            return experiment.strategy_type

    def _prices_through_bar(self, experiment_id: int, bar: DailyBar) -> list:
        with self.session_factory() as session:
            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            if experiment is None:
                raise NotFoundAppError(
                    "Experiment was not found.",
                    details={"experimentId": experiment_id},
                )
            bars = self.market_data_provider.load_range(
                experiment.start_date, experiment.end_date
            )
            prices = []
            for candidate in bars:
                prices.append(candidate.adjusted_close)
                if candidate.date == bar.date:
                    break
            return prices

    def _run_agentic_ai_step(
        self, experiment_id: int, bar: DailyBar, execution_step_id: int
    ) -> None:
        with self.session_factory() as session:
            now = _utcnow()
            timestamp = _bar_timestamp(bar)
            experiment_repository = ExperimentRepository(session)
            execution_step_repository = ExecutionStepRepository(session)
            market_data_repository = MarketDataSnapshotRepository(session)
            portfolio_repository = PortfolioRepository(session)
            strategy_config_repository = StrategyConfigRepository(session)
            trading_decision_repository = TradingDecisionRepository(session)
            agent_log_repository = AgentDecisionLogRepository(session)
            risk_check_repository = RiskCheckRepository(session)
            portfolio_snapshot_repository = PortfolioSnapshotRepository(session)
            metric_snapshot_repository = MetricSnapshotRepository(session)
            trade_repository = TradeRepository(session)

            experiment = experiment_repository.get_by_id(experiment_id)
            portfolio = portfolio_repository.get_by_experiment_id(experiment_id)
            strategy_config = strategy_config_repository.get_by_experiment_id(
                experiment_id
            )
            if experiment is None or portfolio is None or strategy_config is None:
                raise RuntimeError(f"Experiment {experiment_id} is missing state.")

            execution_step = execution_step_repository.get(execution_step_id)
            if execution_step is None:
                raise RuntimeError(f"Execution step {execution_step_id} was not found.")

            market_data = market_data_repository.add(
                MarketDataSnapshotModel(
                    execution_step_id=execution_step.id,
                    experiment_id=experiment_id,
                    timestamp=timestamp,
                    symbol="SPY",
                    price=bar.adjusted_close,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.adjusted_close,
                    volume=bar.volume,
                    moving_average=None,
                    rsi=None,
                    raw_data_json=bar.raw,
                    created_at=now,
                )
            )
            session.flush()

            agent_context = AgentContext(
                experiment_id=experiment_id,
                execution_step_id=execution_step.id,
                symbol="SPY",
                bar=bar,
                cash=portfolio.cash,
                position_quantity=portfolio.position_quantity,
                current_portfolio_value=portfolio.current_portfolio_value,
                confidence_threshold=strategy_config.confidence_threshold,
                parameters_json=strategy_config.parameters_json,
                agent_mode=strategy_config.agent_mode or AgentMode.SINGLE_AGENT,
                model_name=strategy_config.model_name,
            )
            agent_result = self.agent_strategy.decide(agent_context)
            agent_decision = agent_result.decision
            trading_decision = trading_decision_repository.add(
                TradingDecisionModel(
                    execution_step_id=execution_step.id,
                    experiment_id=experiment_id,
                    market_data_snapshot_id=market_data.id,
                    source_type=DecisionSourceType.AGENT,
                    source_name=self.agent_strategy.source_name,
                    action=agent_decision.action,
                    symbol=agent_decision.symbol,
                    suggested_quantity=None,
                    suggested_notional=None,
                    confidence=agent_decision.confidence,
                    reason=agent_decision.reason,
                    raw_decision_json=agent_decision.raw_decision_json,
                    created_at=now,
                )
            )
            session.flush()

            log_payload = agent_result.log_payload
            agent_log_repository.add(
                AgentDecisionLogModel(
                    execution_step_id=execution_step.id,
                    experiment_id=experiment_id,
                    trading_decision_id=trading_decision.id,
                    agent_mode=strategy_config.agent_mode or AgentMode.SINGLE_AGENT,
                    agent_step_name=AgentStepName.SINGLE_DECISION_AGENT,
                    agent_name=log_payload.agent_name,
                    prompt_version=log_payload.prompt_version,
                    model_name=log_payload.model_name,
                    model_version=log_payload.model_version,
                    input_json=log_payload.input_json,
                    prompt_text=log_payload.prompt_text,
                    raw_output_text=log_payload.raw_output_text,
                    parsed_output_json=log_payload.parsed_output_json,
                    parsing_status=log_payload.parsing_status,
                    repair_prompt_text=log_payload.repair_prompt_text,
                    repair_raw_output_text=log_payload.repair_raw_output_text,
                    created_at=now,
                )
            )
            session.flush()

            risk_result = self.risk_validator.evaluate(
                agent_decision, portfolio, bar.adjusted_close
            )
            risk_check = risk_check_repository.add(
                RiskCheckModel(
                    execution_step_id=execution_step.id,
                    experiment_id=experiment_id,
                    trading_decision_id=trading_decision.id,
                    approved=risk_result.approved,
                    final_action=risk_result.final_action,
                    final_quantity=risk_result.final_quantity,
                    final_notional=risk_result.final_notional,
                    rejection_reason=risk_result.rejection_reason,
                    rules_triggered_json=risk_result.rules_triggered_json,
                    created_at=now,
                )
            )
            session.flush()

            execution_result = self.execution_provider.execute_if_applicable(
                risk_result=risk_result,
                portfolio=portfolio,
                experiment_id=experiment_id,
                execution_step_id=execution_step.id,
                risk_check_id=risk_check.id,
                timestamp=timestamp,
                price=bar.adjusted_close,
                now=now,
            )
            if execution_result.order is not None and execution_result.trade is not None:
                session.add(execution_result.order)
                session.flush()
                execution_result.trade.order_id = execution_result.order.id
                session.add(execution_result.trade)
                session.flush()

            position_quantity = portfolio.position_quantity or Decimal("0")
            current_position_value = (
                position_quantity * bar.adjusted_close
            ).quantize(Decimal("0.0001"))
            current_portfolio_value = (
                portfolio.cash + current_position_value
            ).quantize(Decimal("0.0001"))
            portfolio.current_price = bar.adjusted_close
            portfolio.current_position_value = current_position_value
            portfolio.current_portfolio_value = current_portfolio_value
            portfolio.updated_at = now

            if execution_result.trade is not None:
                execution_result.trade.portfolio_value_after_trade = (
                    current_portfolio_value
                )

            previous_values = [
                snapshot.total_portfolio_value
                for snapshot in portfolio_snapshot_repository.list_by_experiment(
                    experiment_id
                )
                if snapshot.total_portfolio_value is not None
            ]

            portfolio_snapshot_repository.add(
                PortfolioSnapshotModel(
                    execution_step_id=execution_step.id,
                    experiment_id=experiment_id,
                    timestamp=timestamp,
                    cash=portfolio.cash,
                    position_symbol=portfolio.position_symbol,
                    position_quantity=portfolio.position_quantity,
                    position_market_value=current_position_value,
                    total_portfolio_value=current_portfolio_value,
                    current_price=bar.adjusted_close,
                    created_at=now,
                )
            )

            metrics = self.metric_calculator.calculate(
                initial_capital=experiment.initial_capital,
                current_portfolio_value=current_portfolio_value,
                previous_portfolio_values=previous_values,
                number_of_trades=trade_repository.count_by_experiment(experiment_id),
            )
            metric_snapshot_repository.add(
                MetricSnapshotModel(
                    execution_step_id=execution_step.id,
                    experiment_id=experiment_id,
                    timestamp=timestamp,
                    total_return=metrics.total_return,
                    profit_loss=metrics.profit_loss,
                    number_of_trades=metrics.number_of_trades,
                    max_drawdown=metrics.max_drawdown,
                    buy_and_hold_return=metrics.buy_and_hold_return,
                    difference_to_buy_and_hold=metrics.difference_to_buy_and_hold,
                    created_at=now,
                )
            )

            execution_step.status = ExecutionStepStatus.COMPLETED
            execution_step.completed_at = now
            session.commit()

    def _is_final_bar(self, experiment_id: int, sequence_number: int) -> bool:
        with self.session_factory() as session:
            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            if experiment is None:
                raise NotFoundAppError(
                    "Experiment was not found.",
                    details={"experimentId": experiment_id},
                )
            bars = self.market_data_provider.load_range(
                experiment.start_date, experiment.end_date
            )
            return sequence_number >= len(bars)

    def _complete_experiment(self, experiment_id: int) -> None:
        with self.session_factory() as session:
            self._mark_completed_in_session(session, experiment_id)
            session.commit()

    def _mark_completed_in_session(self, session: Session, experiment_id: int) -> None:
        now = _utcnow()
        experiment = ExperimentRepository(session).get_by_id(experiment_id)
        if experiment is None:
            raise NotFoundAppError(
                "Experiment was not found.",
                details={"experimentId": experiment_id},
            )
        if experiment.status is not ExperimentStatus.COMPLETED:
            experiment.status = ExperimentStatus.COMPLETED
            experiment.updated_at = now
            SystemEventLogRepository(session).add(
                SystemEventLogModel(
                    execution_step_id=None,
                    experiment_id=experiment_id,
                    timestamp=now,
                    level=EventLevel.INFO,
                    event_type=SystemEventType.EXPERIMENT_COMPLETED,
                    message="Experiment completed.",
                    details_json={"experimentId": experiment_id},
                    created_at=now,
                )
            )

    def _persist_failure(
        self,
        experiment_id: int,
        execution_step_id: int | None,
        exc: Exception | None = None,
    ) -> None:
        with self.session_factory() as session:
            now = _utcnow()
            if execution_step_id is not None:
                step = ExecutionStepRepository(session).get(execution_step_id)
                if step is not None:
                    step.status = ExecutionStepStatus.FAILED
                    step.completed_at = now
                    step.error_message = "Manual historical execution step failed."

            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            if experiment is not None:
                experiment.status = ExperimentStatus.FAILED
                experiment.updated_at = now
                SystemEventLogRepository(session).add(
                    SystemEventLogModel(
                        execution_step_id=execution_step_id,
                        experiment_id=experiment_id,
                        timestamp=now,
                        level=EventLevel.ERROR,
                        event_type=SystemEventType.EXPERIMENT_FAILED,
                        message="Experiment failed.",
                        details_json=self._failure_details(experiment_id, exc),
                        created_at=now,
                    )
                )
            session.commit()

    def _failure_details(self, experiment_id: int, exc: Exception | None) -> dict:
        details = {"experimentId": experiment_id}
        if isinstance(exc, MarketDataUnavailableError):
            details["errorCode"] = "MARKET_DATA_MISSING"
            details["providerDetails"] = exc.details
        elif isinstance(exc, MarketDataProviderError):
            details["errorCode"] = "MARKET_DATA_PROVIDER_ERROR"
            details["providerDetails"] = exc.details
        return details
