from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.errors import (
    ExperimentStepAlreadyRunningAppError,
    InvalidExperimentConfigurationAppError,
    InvalidStatusAppError,
    NotFoundAppError,
)
from app.domain.assets import SPY_SYMBOL
from app.domain.assets import is_supported_equity_symbol
from app.domain.enums import (
    AgentMode,
    DecisionSourceType,
    BrokerName,
    BrokerSyncStatus,
    EventDecisionStatus,
    EventLevel,
    ExecutionStepStatus,
    ExperimentMode,
    ExperimentStatus,
    FinalAction,
    StrategyType,
    SystemEventType,
    TradeAction,
    TradingFrequency,
    TriggerType,
)
from app.modules.agents.errors import AgentProviderConfigurationError
from app.modules.agents.pipeline_agent import AgentDecisionPipeline
from app.modules.agents.provider_factory import (
    create_scads_agent_provider,
    create_scads_pipeline_provider,
)
from app.modules.agents.single_agent import SingleAgent
from app.modules.agents.types import AgentContext
from app.modules.broker.broker_adapter import BrokerAdapter, BrokerOrderResult
from app.modules.broker.errors import BrokerConfigurationError, BrokerProviderError
from app.modules.broker.factory import create_broker_adapter
from app.modules.execution.metrics import BasicMetricCalculator
from app.modules.execution.paper_provider import PaperExecutionProvider
from app.modules.execution.risk import BuyAndHoldRiskValidator, RiskResult
from app.modules.execution.step_runner import StepRunResult
from app.modules.market_data.factory import create_market_data_provider
from app.modules.market_data.factory import create_intraday_market_data_provider
from app.modules.market_data.hourly_bars import aggregate_hourly_bar
from app.modules.market_data.intraday_provider import (
    OPENING_RANGE_END,
    IntradayBar,
    IntradayMarketDataProvider,
)
from app.modules.market_data.errors import (
    MarketDataProviderError,
    MarketDataUnavailableError,
)
from app.modules.market_data.provider import MarketDataProvider
from app.modules.market_data.trading_calendar import UsEquitiesTradingCalendar
from app.modules.strategies.buy_and_hold import BuyAndHoldStrategy
from app.modules.strategies.agentic_ai_strategy import AgenticAIStrategy
from app.modules.strategies.moving_average import (
    DEFAULT_MOVING_AVERAGE_WINDOW,
    MovingAverageStrategy,
)
from app.modules.strategies.opening_range_breakout import (
    OpeningRangeBreakoutState,
    OpeningRangeBreakoutStrategy,
)
from app.modules.strategies.paper_trading_smoke_test import (
    PaperTradingSmokeTestStrategy,
)
from app.persistence.database import create_session_factory
from app.persistence.models import (
    AgentDecisionLogModel,
    ExecutionStepModel,
    BrokerSyncLogModel,
    EventDecisionModel,
    MarketDataSnapshotModel,
    MetricSnapshotModel,
    NewsEventModel,
    PortfolioModel,
    PortfolioSnapshotModel,
    RiskCheckModel,
    SystemEventLogModel,
    TradeModel,
    TradingDecisionModel,
)
from app.persistence.repositories import (
    AgentDecisionLogRepository,
    ExecutionStepRepository,
    BrokerSyncLogRepository,
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

NEW_YORK_TZ = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class PaperStepFailure:
    error_code: str
    message: str
    broker_result: BrokerOrderResult | None = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PaperTradingStepRunner:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        market_data_provider: MarketDataProvider | None = None,
        intraday_provider: IntradayMarketDataProvider | None = None,
        broker_adapter: BrokerAdapter | None = None,
        agent_strategy: AgenticAIStrategy | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session_factory = session_factory or create_session_factory()
        self.settings = settings or get_settings()
        self.market_data_provider = market_data_provider or create_market_data_provider(
            self.settings
        )
        self.intraday_provider = intraday_provider or create_intraday_market_data_provider(
            self.settings
        )
        self.broker_adapter = broker_adapter
        self.buy_and_hold_strategy = BuyAndHoldStrategy()
        self.moving_average_strategy = MovingAverageStrategy()
        self.orb_strategy = OpeningRangeBreakoutStrategy()
        self.agent_strategy = agent_strategy
        self.smoke_test_strategy = PaperTradingSmokeTestStrategy()
        self.risk_validator = BuyAndHoldRiskValidator()
        self.metric_calculator = BasicMetricCalculator()

    def run_next_step(
        self,
        experiment_id: int,
        trigger_type: TriggerType = TriggerType.MANUAL,
        scheduled_for: datetime | None = None,
    ) -> StepRunResult:
        execution_step_id: int | None = None
        try:
            broker_adapter = self.broker_adapter or self._create_broker_adapter()
            execution_step_id = self._validate_and_create_step(
                experiment_id, trigger_type, scheduled_for
            )
            failure = self._run_step_artifacts(
                experiment_id, execution_step_id, broker_adapter
            )
            if failure is not None:
                return StepRunResult(
                    experiment_id=experiment_id,
                    execution_step_id=execution_step_id,
                    status=ExecutionStepStatus.FAILED,
                    message=failure.message,
                )
            return StepRunResult(
                experiment_id=experiment_id,
                execution_step_id=execution_step_id,
                status=ExecutionStepStatus.COMPLETED,
                message="Paper trading execution step completed.",
            )
        except (
            ExperimentStepAlreadyRunningAppError,
            InvalidExperimentConfigurationAppError,
            InvalidStatusAppError,
            NotFoundAppError,
        ):
            raise
        except AgentProviderConfigurationError as exc:
            self._persist_failure(
                experiment_id,
                execution_step_id,
                error_code="AGENT_PROVIDER_CONFIGURATION_ERROR",
                message=exc.message,
                provider_details=exc.details,
                fail_experiment=True,
                event_type=SystemEventType.EXPERIMENT_FAILED,
            )
            raise InvalidExperimentConfigurationAppError(
                exc.message,
                details=exc.details,
            ) from exc
        except MarketDataUnavailableError as exc:
            self._persist_failure(
                experiment_id,
                execution_step_id,
                error_code="MARKET_DATA_MISSING",
                message=exc.message,
                provider_details=exc.details,
                fail_experiment=False,
                event_type=SystemEventType.MARKET_DATA_MISSING,
            )
            raise
        except MarketDataProviderError as exc:
            self._persist_failure(
                experiment_id,
                execution_step_id,
                error_code="MARKET_DATA_PROVIDER_ERROR",
                message=exc.message,
                provider_details=exc.details,
                fail_experiment=False,
                event_type=SystemEventType.MARKET_DATA_MISSING,
            )
            raise
        except BrokerProviderError as exc:
            self._persist_failure(
                experiment_id,
                execution_step_id,
                error_code="BROKER_PROVIDER_ERROR",
                message=exc.message,
                provider_details=exc.details,
                fail_experiment=False,
                event_type=SystemEventType.ORDER_FAILED,
            )
            raise
        except Exception as exc:
            self._persist_failure(
                experiment_id,
                execution_step_id,
                error_code="BROKER_PROVIDER_ERROR",
                message=str(exc),
                fail_experiment=False,
                event_type=SystemEventType.ORDER_FAILED,
            )
            raise

    def run_event_step(
        self,
        experiment_id: int,
        event_id: int,
        scheduled_for: datetime | None = None,
    ) -> StepRunResult:
        broker_adapter = self.broker_adapter or self._create_broker_adapter()
        execution_step_id = self._validate_and_create_step(
            experiment_id,
            TriggerType.EVENT,
            scheduled_for,
        )
        failure = self._run_step_artifacts(
            experiment_id,
            execution_step_id,
            broker_adapter,
            event_id=event_id,
        )
        return StepRunResult(
            experiment_id=experiment_id,
            execution_step_id=execution_step_id,
            status=ExecutionStepStatus.FAILED
            if failure is not None
            else ExecutionStepStatus.COMPLETED,
            message=failure.message
            if failure is not None
            else "Event-triggered paper trading step completed.",
        )

    def _create_broker_adapter(self) -> BrokerAdapter:
        try:
            return create_broker_adapter(self.settings)
        except BrokerConfigurationError as exc:
            raise InvalidExperimentConfigurationAppError(
                exc.message,
                details=exc.details,
            ) from exc

    def _validate_and_create_step(
        self,
        experiment_id: int,
        trigger_type: TriggerType,
        scheduled_for: datetime | None,
    ) -> int:
        if trigger_type not in {
            TriggerType.MANUAL,
            TriggerType.SCHEDULED,
            TriggerType.EVENT,
        }:
            raise InvalidExperimentConfigurationAppError(
                "Paper trading supports manual, scheduled, and event execution only.",
                details={"triggerType": trigger_type.value},
            )
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
            strategy_config = StrategyConfigRepository(session).get_by_experiment_id(
                experiment_id
            )
            if strategy_config is None:
                raise InvalidExperimentConfigurationAppError(
                    "Experiment is missing strategy configuration.",
                    details={"experimentId": experiment_id},
                )
            if not self._is_supported_experiment(experiment, trigger_type):
                raise InvalidExperimentConfigurationAppError(
                    "Paper trading supports configured equity symbols for "
                    "Buy-and-Hold daily, Moving Average daily, and Agentic AI "
                    "daily/hourly; Opening Range Breakout and smoke-test remain "
                    "SPY-only.",
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
            if not lock_acquired or execution_step_repository.has_running_step(
                experiment_id
            ):
                raise ExperimentStepAlreadyRunningAppError(
                    "Experiment already has a step in progress.",
                    details={"experimentId": experiment_id},
                )

            now = _utcnow()
            step_scheduled_for = scheduled_for or now
            if (
                trigger_type is TriggerType.SCHEDULED
                and execution_step_repository.has_step_for_scheduled_slot(
                    experiment_id, step_scheduled_for
                )
            ):
                raise ExperimentStepAlreadyRunningAppError(
                    "Experiment already has a step for the scheduled paper trading slot.",
                    details={
                        "experimentId": experiment_id,
                        "scheduledFor": step_scheduled_for.isoformat(),
                    },
                )

            execution_step = execution_step_repository.add(
                ExecutionStepModel(
                    experiment_id=experiment_id,
                    scheduled_for=step_scheduled_for,
                    started_at=now,
                    completed_at=None,
                    status=ExecutionStepStatus.RUNNING,
                    trigger_type=trigger_type,
                    sequence_number=execution_step_repository.max_sequence_number(
                        experiment_id
                    )
                    + 1,
                    error_message=None,
                    created_at=now,
                )
            )
            session.flush()
            execution_step_id = execution_step.id
            session.commit()
            return execution_step_id

    def _is_supported_experiment(self, experiment, trigger_type: TriggerType) -> bool:
        if experiment.mode is not ExperimentMode.PAPER_TRADING:
            return False
        if (
            experiment.strategy_type is StrategyType.BUY_AND_HOLD
            and experiment.trading_frequency is TradingFrequency.DAILY
        ):
            return is_supported_equity_symbol(experiment.asset_symbol)
        if (
            experiment.strategy_type is StrategyType.MOVING_AVERAGE
            and experiment.trading_frequency is TradingFrequency.DAILY
        ):
            return is_supported_equity_symbol(experiment.asset_symbol)
        if (
            experiment.strategy_type is StrategyType.AGENTIC_AI
            and experiment.trading_frequency
            in {TradingFrequency.DAILY, TradingFrequency.HOURLY}
        ):
            return is_supported_equity_symbol(experiment.asset_symbol)
        if (
            experiment.strategy_type is StrategyType.OPENING_RANGE_BREAKOUT
            and experiment.trading_frequency is TradingFrequency.INTRADAY_5_MIN
        ):
            return (
                is_supported_equity_symbol(experiment.asset_symbol)
                and trigger_type is TriggerType.SCHEDULED
            )
        if experiment.strategy_type is not StrategyType.PAPER_TRADING_SMOKE_TEST:
            return False
        return (
            self.settings.paper_trading_test_mode_enabled
            and trigger_type is TriggerType.SCHEDULED
            and experiment.trading_frequency is TradingFrequency.TEST_1_MIN
            and experiment.asset_symbol == SPY_SYMBOL
        )

    def _run_step_artifacts(
        self,
        experiment_id: int,
        execution_step_id: int,
        broker_adapter: BrokerAdapter,
        event_id: int | None = None,
    ) -> PaperStepFailure | None:
        with self.session_factory() as session:
            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            if experiment is None:
                raise RuntimeError(f"Experiment {experiment_id} is missing state.")
            strategy_type = experiment.strategy_type
        if strategy_type is StrategyType.OPENING_RANGE_BREAKOUT:
            return self._run_orb_step_artifacts(
                experiment_id,
                execution_step_id,
                broker_adapter,
            )
        if strategy_type is StrategyType.AGENTIC_AI:
            return self._run_agentic_ai_step_artifacts(
                experiment_id,
                execution_step_id,
                broker_adapter,
                event_id=event_id,
            )
        return self._run_daily_step_artifacts(
            experiment_id,
            execution_step_id,
            broker_adapter,
        )

    def _run_daily_step_artifacts(
        self,
        experiment_id: int,
        execution_step_id: int,
        broker_adapter: BrokerAdapter,
    ) -> PaperStepFailure | None:
        with self.session_factory() as session:
            now = _utcnow()
            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            portfolio = PortfolioRepository(session).get_by_experiment_id(experiment_id)
            strategy_config = StrategyConfigRepository(session).get_by_experiment_id(
                experiment_id
            )
            execution_step = ExecutionStepRepository(session).get(execution_step_id)
            if (
                experiment is None
                or portfolio is None
                or strategy_config is None
                or execution_step is None
            ):
                raise RuntimeError(f"Experiment {experiment_id} is missing state.")
            symbol = experiment.asset_symbol
            bar = self.market_data_provider.get_latest_bar(symbol)

            moving_average = self._moving_average_for_step(experiment, strategy_config, bar)
            market_data = MarketDataSnapshotRepository(session).add(
                MarketDataSnapshotModel(
                    execution_step_id=execution_step_id,
                    experiment_id=experiment_id,
                    timestamp=now,
                    symbol=symbol,
                    price=bar.adjusted_close,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.adjusted_close,
                    volume=bar.volume,
                    moving_average=moving_average,
                    rsi=None,
                    raw_data_json=bar.raw,
                    created_at=now,
                )
            )
            session.flush()

            strategy_decision = self._decide(
                experiment.strategy_type,
                portfolio,
                symbol=symbol,
                price=bar.adjusted_close,
                moving_average=moving_average,
                moving_average_window=(
                    strategy_config.moving_average_window
                    or DEFAULT_MOVING_AVERAGE_WINDOW
                ),
            )
            trading_decision = TradingDecisionRepository(session).add(
                TradingDecisionModel(
                    execution_step_id=execution_step_id,
                    experiment_id=experiment_id,
                    market_data_snapshot_id=market_data.id,
                    source_type=DecisionSourceType.STRATEGY,
                    source_name=self._source_name(experiment.strategy_type),
                    action=strategy_decision.action,
                    symbol=strategy_decision.symbol,
                    suggested_quantity=None,
                    suggested_notional=None,
                    confidence=Decimal("1.0000"),
                    reason=strategy_decision.reason,
                    raw_decision_json=self._raw_decision_json(
                        experiment.strategy_type,
                        portfolio.position_quantity,
                        moving_average=moving_average,
                        moving_average_window=(
                            strategy_config.moving_average_window
                            or DEFAULT_MOVING_AVERAGE_WINDOW
                        ),
                    ),
                    created_at=now,
                )
            )
            session.flush()

            risk_result = self.risk_validator.evaluate(
                strategy_decision,
                portfolio,
                bar.adjusted_close,
            )
            if experiment.strategy_type is StrategyType.PAPER_TRADING_SMOKE_TEST:
                risk_result = self._smoke_test_risk_result(
                    strategy_decision.action,
                    portfolio,
                    bar.adjusted_close,
                )
            risk_check = RiskCheckRepository(session).add(
                RiskCheckModel(
                    execution_step_id=execution_step_id,
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

            if self._requires_broker_submission(risk_result):
                risk_check_id = risk_check.id
                session.commit()
                return self._run_broker_execution(
                    experiment_id=experiment_id,
                    execution_step_id=execution_step_id,
                    broker_adapter=broker_adapter,
                    risk_result=risk_result,
                    risk_check_id=risk_check_id,
                    price=bar.adjusted_close,
                    symbol=symbol,
                )

            self._persist_snapshot_and_metrics(
                session=session,
                experiment_id=experiment_id,
                execution_step_id=execution_step_id,
                experiment=experiment,
                portfolio=portfolio,
                price=bar.adjusted_close,
                timestamp=now,
                trade=None,
            )
            execution_step.status = ExecutionStepStatus.COMPLETED
            execution_step.completed_at = now
            session.commit()
            return None

    def _run_orb_step_artifacts(
        self,
        experiment_id: int,
        execution_step_id: int,
        broker_adapter: BrokerAdapter,
    ) -> PaperStepFailure | None:
        with self.session_factory() as session:
            execution_step = ExecutionStepRepository(session).get(execution_step_id)
            if execution_step is None or execution_step.scheduled_for is None:
                raise RuntimeError("Scheduled ORB paper step is missing its slot.")
            scheduled_for = execution_step.scheduled_for
            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            if experiment is None:
                raise RuntimeError(f"Experiment {experiment_id} is missing state.")
            symbol = experiment.asset_symbol
        bars = self.intraday_provider.load_session_until(
            scheduled_for.date(),
            scheduled_for,
            symbol=symbol,
            frequency=TradingFrequency.INTRADAY_5_MIN,
        )
        bar = bars[-1]
        state = self._orb_state(bars, bar, experiment_id)

        with self.session_factory() as session:
            now = _utcnow()
            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            portfolio = PortfolioRepository(session).get_by_experiment_id(experiment_id)
            strategy_config = StrategyConfigRepository(session).get_by_experiment_id(
                experiment_id
            )
            execution_step = ExecutionStepRepository(session).get(execution_step_id)
            if (
                experiment is None
                or portfolio is None
                or strategy_config is None
                or execution_step is None
            ):
                raise RuntimeError(f"Experiment {experiment_id} is missing state.")

            market_data = MarketDataSnapshotRepository(session).add(
                MarketDataSnapshotModel(
                    execution_step_id=execution_step_id,
                    experiment_id=experiment_id,
                    timestamp=bar.timestamp,
                    symbol=symbol,
                    price=bar.close,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                    moving_average=None,
                    rsi=None,
                    raw_data_json=bar.raw,
                    created_at=now,
                )
            )
            session.flush()

            strategy_decision = self.orb_strategy.decide(
                symbol=symbol,
                close=bar.close,
                position_quantity=portfolio.position_quantity,
                state=state,
            )
            trading_decision = TradingDecisionRepository(session).add(
                TradingDecisionModel(
                    execution_step_id=execution_step_id,
                    experiment_id=experiment_id,
                    market_data_snapshot_id=market_data.id,
                    source_type=DecisionSourceType.STRATEGY,
                    source_name=self.orb_strategy.source_name,
                    action=strategy_decision.action,
                    symbol=strategy_decision.symbol,
                    suggested_quantity=None,
                    suggested_notional=None,
                    confidence=Decimal("1.0000"),
                    reason=strategy_decision.reason,
                    raw_decision_json=strategy_decision.raw_decision_json,
                    created_at=now,
                )
            )
            session.flush()

            risk_result = self.risk_validator.evaluate(
                strategy_decision,
                portfolio,
                bar.close,
            )
            risk_check = RiskCheckRepository(session).add(
                RiskCheckModel(
                    execution_step_id=execution_step_id,
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

            if self._requires_broker_submission(risk_result):
                risk_check_id = risk_check.id
                session.commit()
                return self._run_broker_execution(
                    experiment_id=experiment_id,
                    execution_step_id=execution_step_id,
                    broker_adapter=broker_adapter,
                    risk_result=risk_result,
                    risk_check_id=risk_check_id,
                    price=bar.close,
                    symbol=symbol,
                )

            self._persist_snapshot_and_metrics(
                session=session,
                experiment_id=experiment_id,
                execution_step_id=execution_step_id,
                experiment=experiment,
                portfolio=portfolio,
                price=bar.close,
                timestamp=bar.timestamp,
                trade=None,
            )
            execution_step.status = ExecutionStepStatus.COMPLETED
            execution_step.completed_at = now
            session.commit()
            return None

    def _run_agentic_ai_step_artifacts(
        self,
        experiment_id: int,
        execution_step_id: int,
        broker_adapter: BrokerAdapter,
        event_id: int | None = None,
    ) -> PaperStepFailure | None:
        with self.session_factory() as session:
            now = _utcnow()
            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            portfolio = PortfolioRepository(session).get_by_experiment_id(experiment_id)
            strategy_config = StrategyConfigRepository(session).get_by_experiment_id(
                experiment_id
            )
            execution_step = ExecutionStepRepository(session).get(execution_step_id)
            if (
                experiment is None
                or portfolio is None
                or strategy_config is None
                or execution_step is None
            ):
                raise RuntimeError(f"Experiment {experiment_id} is missing state.")

            selected_model = strategy_config.model_name or self.settings.scadsai_default_model
            agent_mode = strategy_config.agent_mode or AgentMode.SINGLE_AGENT
            symbol = experiment.asset_symbol
            bar = self._agent_market_bar(experiment, execution_step)
            agent_strategy = self._paper_agent_strategy(selected_model, agent_mode)
            market_data = MarketDataSnapshotRepository(session).add(
                MarketDataSnapshotModel(
                    execution_step_id=execution_step_id,
                    experiment_id=experiment_id,
                    timestamp=bar.timestamp or now,
                    symbol=symbol,
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
                execution_step_id=execution_step_id,
                symbol=symbol,
                bar=bar,
                cash=portfolio.cash,
                position_quantity=portfolio.position_quantity,
                current_portfolio_value=portfolio.current_portfolio_value,
                confidence_threshold=strategy_config.confidence_threshold,
                parameters_json=strategy_config.parameters_json,
                agent_mode=agent_mode,
                model_name=selected_model,
                event_context=self._event_context(session, event_id),
            )
            agent_result = agent_strategy.decide(agent_context)
            agent_decision = agent_result.decision
            trading_decision = TradingDecisionRepository(session).add(
                TradingDecisionModel(
                    execution_step_id=execution_step_id,
                    experiment_id=experiment_id,
                    market_data_snapshot_id=market_data.id,
                    source_type=DecisionSourceType.AGENT,
                    source_name=agent_strategy.source_name,
                    action=agent_decision.action,
                    symbol=agent_decision.symbol,
                    suggested_quantity=None,
                    suggested_notional=None,
                    confidence=agent_decision.confidence,
                    trade_intent=agent_decision.trade_intent,
                    target_exposure_pct=agent_decision.target_exposure_pct,
                    primary_driver=agent_decision.primary_driver,
                    new_information=agent_decision.new_information,
                    reason=agent_decision.reason,
                    raw_decision_json=agent_decision.raw_decision_json,
                    created_at=now,
                )
            )
            session.flush()

            log_payloads = agent_result.log_payloads or (agent_result.log_payload,)
            for log_payload in log_payloads:
                AgentDecisionLogRepository(session).add(
                    AgentDecisionLogModel(
                        execution_step_id=execution_step_id,
                        experiment_id=experiment_id,
                        trading_decision_id=trading_decision.id,
                        agent_mode=agent_mode,
                        agent_step_name=log_payload.agent_step_name,
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
            self._mark_event_decision_triggered(
                session=session,
                event_id=event_id,
                experiment_id=experiment_id,
                execution_step_id=execution_step_id,
                trading_decision_id=trading_decision.id,
                now=now,
            )

            risk_result = self.risk_validator.evaluate_target_exposure(
                agent_decision,
                portfolio,
                bar.adjusted_close,
            )
            risk_check = RiskCheckRepository(session).add(
                RiskCheckModel(
                    execution_step_id=execution_step_id,
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

            if self._requires_broker_submission(risk_result):
                risk_check_id = risk_check.id
                session.commit()
                return self._run_broker_execution(
                    experiment_id=experiment_id,
                    execution_step_id=execution_step_id,
                    broker_adapter=broker_adapter,
                    risk_result=risk_result,
                    risk_check_id=risk_check_id,
                    price=bar.adjusted_close,
                    symbol=symbol,
                )

            self._persist_snapshot_and_metrics(
                session=session,
                experiment_id=experiment_id,
                execution_step_id=execution_step_id,
                experiment=experiment,
                portfolio=portfolio,
                price=bar.adjusted_close,
                timestamp=bar.timestamp or now,
                trade=None,
            )
            execution_step.status = ExecutionStepStatus.COMPLETED
            execution_step.completed_at = now
            session.commit()
            return None

    def _decide(
        self,
        strategy_type: StrategyType,
        portfolio: PortfolioModel,
        *,
        symbol: str,
        price: Decimal,
        moving_average: Decimal | None,
        moving_average_window: int,
    ):
        if strategy_type is StrategyType.PAPER_TRADING_SMOKE_TEST:
            return self.smoke_test_strategy.decide(
                symbol=SPY_SYMBOL,
                position_quantity=portfolio.position_quantity,
            )
        if strategy_type is StrategyType.MOVING_AVERAGE:
            return self.moving_average_strategy.decide(
                symbol=symbol,
                price=price,
                moving_average=moving_average,
                position_quantity=portfolio.position_quantity,
                window=moving_average_window,
            )
        return self.buy_and_hold_strategy.decide(
            symbol=symbol,
            position_quantity=portfolio.position_quantity,
        )

    def _paper_agent_strategy(
        self, model_name: str, agent_mode: AgentMode
    ) -> AgenticAIStrategy:
        if self.agent_strategy is not None:
            return self.agent_strategy
        if agent_mode is AgentMode.PIPELINE:
            provider = create_scads_pipeline_provider(self.settings, model_name)
            return AgenticAIStrategy(
                pipeline=AgentDecisionPipeline(
                    provider=provider,
                    market_data_provider=self.market_data_provider,
                )
            )
        provider = create_scads_agent_provider(self.settings, model_name)
        return AgenticAIStrategy(agent=SingleAgent(provider=provider))

    def _agent_market_bar(
        self,
        experiment,
        execution_step: ExecutionStepModel,
    ):
        if experiment.trading_frequency is TradingFrequency.HOURLY:
            return self._load_hourly_agent_bar(experiment.asset_symbol, execution_step)
        return self.market_data_provider.get_latest_bar(experiment.asset_symbol)

    def _event_context(self, session: Session, event_id: int | None) -> dict | None:
        if event_id is None:
            return None
        event = session.get(NewsEventModel, event_id)
        if event is None:
            return None
        return {
            "eventId": event.id,
            "externalEventId": event.external_event_id,
            "provider": event.provider,
            "timestamp": event.timestamp.isoformat(),
            "headline": event.headline,
            "summary": event.summary,
            "source": event.source,
            "eventType": event.event_type.value,
            "severity": event.severity.value,
            "affectedSymbols": event.affected_symbols_json,
        }

    def _mark_event_decision_triggered(
        self,
        *,
        session: Session,
        event_id: int | None,
        experiment_id: int,
        execution_step_id: int,
        trading_decision_id: int,
        now: datetime,
    ) -> None:
        if event_id is None:
            return
        event_decision = (
            session.query(EventDecisionModel)
            .filter(
                EventDecisionModel.event_id == event_id,
                EventDecisionModel.experiment_id == experiment_id,
            )
            .one_or_none()
        )
        if event_decision is None:
            event_decision = EventDecisionModel(
                event_id=event_id,
                experiment_id=experiment_id,
                execution_step_id=execution_step_id,
                trading_decision_id=trading_decision_id,
                status=EventDecisionStatus.TRIGGERED,
                reason="Event-triggered agent run executed.",
                created_at=now,
                updated_at=now,
            )
            session.add(event_decision)
            return
        event_decision.execution_step_id = execution_step_id
        event_decision.trading_decision_id = trading_decision_id
        event_decision.status = EventDecisionStatus.TRIGGERED
        event_decision.reason = "Event-triggered agent run executed."
        event_decision.updated_at = now

    def _load_hourly_agent_bar(self, symbol: str, execution_step: ExecutionStepModel):
        scheduled_for = execution_step.scheduled_for or _utcnow()
        local_slot = scheduled_for.replace(tzinfo=timezone.utc).astimezone(NEW_YORK_TZ)
        sessions = UsEquitiesTradingCalendar().sessions_between(
            local_slot.date(),
            local_slot.date(),
        )
        if not sessions:
            raise MarketDataUnavailableError(
                "No US equities trading session exists for the hourly AI slot.",
                details={"scheduledFor": scheduled_for.isoformat()},
            )
        session = sessions[0]
        bars = self.intraday_provider.load_session_until(
            local_slot.date(),
            local_slot.replace(tzinfo=None) + timedelta(minutes=55),
            symbol=symbol,
        )
        return aggregate_hourly_bar(
            session=session,
            bars=bars,
            window_start=local_slot.replace(tzinfo=None),
            symbol=symbol,
        )

    def _source_name(self, strategy_type: StrategyType) -> str:
        if strategy_type is StrategyType.PAPER_TRADING_SMOKE_TEST:
            return self.smoke_test_strategy.source_name
        if strategy_type is StrategyType.MOVING_AVERAGE:
            return self.moving_average_strategy.source_name
        if strategy_type is StrategyType.OPENING_RANGE_BREAKOUT:
            return self.orb_strategy.source_name
        return self.buy_and_hold_strategy.source_name

    def _raw_decision_json(
        self,
        strategy_type: StrategyType,
        position_quantity: Decimal | None,
        *,
        moving_average: Decimal | None = None,
        moving_average_window: int | None = None,
    ) -> dict:
        if strategy_type is StrategyType.PAPER_TRADING_SMOKE_TEST:
            return {
                "strategy": self.smoke_test_strategy.source_name,
                "diagnosticOnly": True,
                "fixedBuyQuantity": 1,
                "localPositionQuantity": float(position_quantity or Decimal("0")),
            }
        if strategy_type is StrategyType.MOVING_AVERAGE:
            return {
                "strategy": self.moving_average_strategy.source_name,
                "movingAverage": float(moving_average)
                if moving_average is not None
                else None,
                "movingAverageWindow": moving_average_window,
                "reasonCode": (
                    None
                    if moving_average is not None
                    else "INSUFFICIENT_MOVING_AVERAGE_LOOKBACK"
                ),
            }
        return {"strategy": self.buy_and_hold_strategy.source_name}

    def _moving_average_for_step(
        self,
        experiment,
        strategy_config,
        latest_bar,
    ) -> Decimal | None:
        if experiment.strategy_type is not StrategyType.MOVING_AVERAGE:
            return None
        window = strategy_config.moving_average_window or DEFAULT_MOVING_AVERAGE_WINDOW
        lookback_start = latest_bar.date - timedelta(days=(window * 2 + 10))
        bars = self.market_data_provider.load_range(
            lookback_start,
            latest_bar.date,
            symbol=experiment.asset_symbol,
            frequency=TradingFrequency.DAILY,
        )
        eligible = sorted(
            [bar for bar in bars if bar.date <= latest_bar.date],
            key=lambda item: item.date,
        )
        if len(eligible) < window:
            return None
        total = sum((bar.adjusted_close for bar in eligible[-window:]), Decimal("0"))
        return (total / Decimal(window)).quantize(Decimal("0.0001"))

    def _orb_state(
        self,
        bars: list[IntradayBar],
        bar: IntradayBar,
        experiment_id: int,
    ) -> OpeningRangeBreakoutState:
        opening_range_bars = [
            item for item in bars if item.timestamp.time() <= OPENING_RANGE_END
        ]
        opening_range_complete = bar.timestamp.time() > OPENING_RANGE_END
        sessions = UsEquitiesTradingCalendar().sessions_between(
            bar.session_date,
            bar.session_date,
        )
        final_bar = bool(
            sessions and bar.timestamp == sessions[0].expected_bar_start_times[-1]
        )
        return OpeningRangeBreakoutState(
            session_date=bar.session_date,
            opening_range_high=(
                max(item.high for item in opening_range_bars)
                if opening_range_complete and opening_range_bars
                else None
            ),
            opening_range_low=(
                min(item.low for item in opening_range_bars)
                if opening_range_complete and opening_range_bars
                else None
            ),
            opening_range_complete=opening_range_complete,
            final_bar=final_bar,
            round_trip_completed=self._orb_round_trip_completed(
                experiment_id,
                bar.session_date,
            ),
        )

    def _orb_round_trip_completed(self, experiment_id: int, session_date) -> bool:
        with self.session_factory() as session:
            trades = TradeRepository(session).list_by_experiment(experiment_id)
            return any(
                trade.side.value == TradeAction.SELL.value
                and trade.timestamp.date() == session_date
                for trade in trades
            )

    @staticmethod
    def _smoke_test_risk_result(
        action: TradeAction,
        portfolio: PortfolioModel,
        price: Decimal,
    ) -> RiskResult:
        if action is TradeAction.SELL:
            position_quantity = portfolio.position_quantity or Decimal("0")
            if position_quantity <= 0:
                return RiskResult(
                    approved=True,
                    final_action=FinalAction.HOLD,
                    final_quantity=None,
                    final_notional=None,
                    rejection_reason="No SPY position exists to sell.",
                    rules_triggered_json={"reason": "NO_POSITION_TO_SELL"},
                )
            return RiskResult(
                approved=True,
                final_action=FinalAction.SELL,
                final_quantity=position_quantity,
                final_notional=(position_quantity * price).quantize(Decimal("0.0001")),
                rejection_reason=None,
                rules_triggered_json={"reason": "SELL_FULL_POSITION"},
            )
        if action is TradeAction.BUY and portfolio.cash >= price:
            return RiskResult(
                approved=True,
                final_action=FinalAction.BUY,
                final_quantity=Decimal("1"),
                final_notional=price.quantize(Decimal("0.0001")),
                rejection_reason=None,
                rules_triggered_json={"reason": "SMOKE_TEST_FIXED_ONE_SHARE"},
            )
        return RiskResult(
            approved=True,
            final_action=FinalAction.HOLD,
            final_quantity=None,
            final_notional=None,
            rejection_reason="Insufficient cash to buy one SPY share.",
            rules_triggered_json={"reason": "INSUFFICIENT_CASH_FOR_ONE_SHARE"},
        )

    def _run_broker_execution(
        self,
        *,
        experiment_id: int,
        execution_step_id: int,
        broker_adapter: BrokerAdapter,
        risk_result: RiskResult,
        risk_check_id: int,
        price: Decimal,
        symbol: str,
    ) -> PaperStepFailure | None:
        with self.session_factory() as session:
            now = _utcnow()
            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            portfolio = PortfolioRepository(session).get_by_experiment_id(experiment_id)
            execution_step = ExecutionStepRepository(session).get(execution_step_id)
            if experiment is None or portfolio is None or execution_step is None:
                raise RuntimeError(f"Experiment {experiment_id} is missing state.")

            paper_execution = PaperExecutionProvider(broker_adapter).execute_if_applicable(
                session=session,
                risk_result=risk_result,
                portfolio=portfolio,
                experiment_id=experiment_id,
                execution_step_id=execution_step_id,
                risk_check_id=risk_check_id,
                symbol=symbol,
                timestamp=now,
                now=now,
            )
            if paper_execution.order is not None:
                session.add(paper_execution.order)
                session.flush()
            if paper_execution.trade is not None:
                paper_execution.trade.order_id = paper_execution.order.id
                session.add(paper_execution.trade)
                session.flush()

            self._persist_snapshot_and_metrics(
                session=session,
                experiment_id=experiment_id,
                execution_step_id=execution_step_id,
                experiment=experiment,
                portfolio=portfolio,
                price=price,
                timestamp=now,
                trade=paper_execution.trade,
            )

            failure = self._controlled_order_failure(paper_execution.broker_result)
            if failure is not None:
                execution_step.status = ExecutionStepStatus.FAILED
                execution_step.completed_at = now
                execution_step.error_message = failure.message
                experiment.status = ExperimentStatus.FAILED
                experiment.updated_at = now
                SystemEventLogRepository(session).add(
                    self._failure_event(
                        experiment_id=experiment_id,
                        execution_step_id=execution_step_id,
                        failure=failure,
                        now=now,
                    )
                )
                session.commit()
                return failure

            execution_step.status = ExecutionStepStatus.COMPLETED
            execution_step.completed_at = now
            session.commit()
            return None

    def _requires_broker_submission(self, risk_result: RiskResult) -> bool:
        return (
            risk_result.approved
            and risk_result.final_action in {FinalAction.BUY, FinalAction.SELL}
            and risk_result.final_quantity is not None
            and risk_result.final_quantity > 0
        )

    def _persist_snapshot_and_metrics(
        self,
        *,
        session: Session,
        experiment_id: int,
        execution_step_id: int,
        experiment,
        portfolio: PortfolioModel,
        price: Decimal,
        timestamp: datetime,
        trade: TradeModel | None,
    ) -> None:
        current_position_value = (
            (portfolio.position_quantity or Decimal("0")) * price
        ).quantize(Decimal("0.0001"))
        current_portfolio_value = (portfolio.cash + current_position_value).quantize(
            Decimal("0.0001")
        )
        portfolio.current_price = price
        portfolio.current_position_value = current_position_value
        portfolio.current_portfolio_value = current_portfolio_value
        portfolio.updated_at = timestamp
        if trade is not None:
            trade.portfolio_value_after_trade = current_portfolio_value

        previous_values = [
            snapshot.total_portfolio_value
            for snapshot in PortfolioSnapshotRepository(session).list_by_experiment(
                experiment_id
            )
            if snapshot.total_portfolio_value is not None
        ]
        PortfolioSnapshotRepository(session).add(
            PortfolioSnapshotModel(
                execution_step_id=execution_step_id,
                experiment_id=experiment_id,
                timestamp=timestamp,
                cash=portfolio.cash,
                position_symbol=portfolio.position_symbol,
                position_quantity=portfolio.position_quantity,
                position_market_value=current_position_value,
                total_portfolio_value=current_portfolio_value,
                current_price=price,
                created_at=timestamp,
            )
        )
        metrics = self.metric_calculator.calculate(
            initial_capital=experiment.initial_capital,
            current_portfolio_value=current_portfolio_value,
            previous_portfolio_values=previous_values,
            number_of_trades=TradeRepository(session).count_by_experiment(
                experiment_id
            ),
        )
        MetricSnapshotRepository(session).add(
            MetricSnapshotModel(
                execution_step_id=execution_step_id,
                experiment_id=experiment_id,
                timestamp=timestamp,
                total_return=metrics.total_return,
                profit_loss=metrics.profit_loss,
                number_of_trades=metrics.number_of_trades,
                max_drawdown=metrics.max_drawdown,
                buy_and_hold_return=metrics.buy_and_hold_return,
                difference_to_buy_and_hold=metrics.difference_to_buy_and_hold,
                created_at=timestamp,
            )
        )

    def _controlled_order_failure(
        self, broker_result: BrokerOrderResult | None
    ) -> PaperStepFailure | None:
        if broker_result is None:
            return None
        normalized_status = broker_result.status.lower()
        if normalized_status == "rejected":
            return PaperStepFailure(
                error_code="ORDER_REJECTED",
                message="Broker rejected the paper order.",
                broker_result=broker_result,
            )
        if normalized_status not in {
            "accepted",
            "new",
            "pending_new",
            "partially_filled",
            "filled",
            "canceled",
            "cancelled",
            "expired",
        }:
            return PaperStepFailure(
                error_code="ORDER_FAILED",
                message="Broker returned an unsupported order status.",
                broker_result=broker_result,
            )
        return None

    def _persist_failure(
        self,
        experiment_id: int,
        execution_step_id: int | None,
        *,
        error_code: str,
        message: str,
        provider_details: dict | None = None,
        fail_experiment: bool = True,
        event_type: SystemEventType = SystemEventType.EXPERIMENT_FAILED,
    ) -> None:
        with self.session_factory() as session:
            now = _utcnow()
            if execution_step_id is not None:
                step = ExecutionStepRepository(session).get(execution_step_id)
                if step is not None:
                    step.status = ExecutionStepStatus.FAILED
                    step.completed_at = now
                    step.error_message = message

            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            if experiment is not None:
                if fail_experiment:
                    experiment.status = ExperimentStatus.FAILED
                    experiment.updated_at = now
                failure = PaperStepFailure(error_code=error_code, message=message)
                SystemEventLogRepository(session).add(
                    self._failure_event(
                        experiment_id=experiment_id,
                        execution_step_id=execution_step_id,
                        failure=failure,
                        now=now,
                        provider_details=provider_details,
                        event_type=event_type,
                    )
                )
                if (
                    event_type is SystemEventType.ORDER_FAILED
                    and execution_step_id is not None
                ):
                    BrokerSyncLogRepository(session).add(
                        BrokerSyncLogModel(
                            execution_step_id=execution_step_id,
                            experiment_id=experiment_id,
                            timestamp=now,
                            broker_name=BrokerName.ALPACA,
                            sync_status=BrokerSyncStatus.FAILED,
                            broker_cash=None,
                            local_cash=None,
                            broker_positions_json=None,
                            local_positions_json=None,
                            mismatch_details_json={
                                "syncType": "PAPER_ORDER_SUBMIT",
                                "errorCode": error_code,
                                "providerDetails": provider_details or {},
                            },
                            error_message=message,
                            created_at=now,
                        )
                    )
            session.commit()

    def _failure_event(
        self,
        *,
        experiment_id: int,
        execution_step_id: int | None,
        failure: PaperStepFailure,
        now: datetime,
        provider_details: dict | None = None,
        event_type: SystemEventType = SystemEventType.EXPERIMENT_FAILED,
    ) -> SystemEventLogModel:
        broker_result = failure.broker_result
        details = {
            "experimentId": experiment_id,
            "errorCode": failure.error_code,
            "provider": "alpaca",
            "message": failure.message,
        }
        if broker_result is not None:
            details["brokerOrderId"] = broker_result.broker_order_id
            details["brokerStatus"] = broker_result.status
        if provider_details:
            details["providerDetails"] = provider_details
        return SystemEventLogModel(
            execution_step_id=execution_step_id,
            experiment_id=experiment_id,
            timestamp=now,
            level=EventLevel.ERROR,
            event_type=event_type,
            message=(
                "Experiment failed."
                if event_type is SystemEventType.EXPERIMENT_FAILED
                else failure.message
            ),
            details_json=details,
            created_at=now,
        )
