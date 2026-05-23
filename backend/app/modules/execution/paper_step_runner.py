from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.errors import (
    ExperimentStepAlreadyRunningAppError,
    InvalidExperimentConfigurationAppError,
    InvalidStatusAppError,
    NotFoundAppError,
)
from app.domain.enums import (
    DecisionSourceType,
    EventLevel,
    ExecutionStepStatus,
    ExperimentMode,
    ExperimentStatus,
    FinalAction,
    StrategyType,
    SystemEventType,
    TradingFrequency,
    TriggerType,
)
from app.modules.broker.broker_adapter import BrokerAdapter, BrokerOrderResult
from app.modules.broker.errors import BrokerConfigurationError, BrokerProviderError
from app.modules.broker.factory import create_broker_adapter
from app.modules.execution.metrics import BasicMetricCalculator
from app.modules.execution.paper_provider import PaperExecutionProvider
from app.modules.execution.risk import BuyAndHoldRiskValidator, RiskResult
from app.modules.execution.step_runner import StepRunResult
from app.modules.market_data.factory import create_market_data_provider
from app.modules.market_data.provider import MarketDataProvider
from app.modules.strategies.buy_and_hold import BuyAndHoldStrategy
from app.persistence.database import create_session_factory
from app.persistence.models import (
    ExecutionStepModel,
    MarketDataSnapshotModel,
    MetricSnapshotModel,
    PortfolioModel,
    PortfolioSnapshotModel,
    RiskCheckModel,
    SystemEventLogModel,
    TradeModel,
    TradingDecisionModel,
)
from app.persistence.repositories import (
    ExecutionStepRepository,
    ExperimentRepository,
    MarketDataSnapshotRepository,
    MetricSnapshotRepository,
    PortfolioRepository,
    PortfolioSnapshotRepository,
    RiskCheckRepository,
    SystemEventLogRepository,
    TradeRepository,
    TradingDecisionRepository,
)


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
        broker_adapter: BrokerAdapter | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session_factory = session_factory or create_session_factory()
        self.settings = settings or get_settings()
        self.market_data_provider = market_data_provider or create_market_data_provider(
            self.settings
        )
        self.broker_adapter = broker_adapter
        self.strategy = BuyAndHoldStrategy()
        self.risk_validator = BuyAndHoldRiskValidator()
        self.metric_calculator = BasicMetricCalculator()

    def run_next_step(
        self,
        experiment_id: int,
        trigger_type: TriggerType = TriggerType.MANUAL,
    ) -> StepRunResult:
        execution_step_id: int | None = None
        try:
            broker_adapter = self.broker_adapter or self._create_broker_adapter()
            execution_step_id = self._validate_and_create_step(
                experiment_id, trigger_type
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
        except BrokerProviderError as exc:
            self._persist_failure(
                experiment_id,
                execution_step_id,
                error_code="BROKER_PROVIDER_ERROR",
                message=exc.message,
                provider_details=exc.details,
            )
            raise
        except Exception as exc:
            self._persist_failure(
                experiment_id,
                execution_step_id,
                error_code="BROKER_PROVIDER_ERROR",
                message=str(exc),
            )
            raise

    def _create_broker_adapter(self) -> BrokerAdapter:
        try:
            return create_broker_adapter(self.settings)
        except BrokerConfigurationError as exc:
            raise InvalidExperimentConfigurationAppError(
                exc.message,
                details=exc.details,
            ) from exc

    def _validate_and_create_step(
        self, experiment_id: int, trigger_type: TriggerType
    ) -> int:
        if trigger_type is not TriggerType.MANUAL:
            raise InvalidExperimentConfigurationAppError(
                "Paper trading supports manual run-next-step only.",
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
            if (
                experiment.mode is not ExperimentMode.PAPER_TRADING
                or experiment.strategy_type is not StrategyType.BUY_AND_HOLD
                or experiment.trading_frequency is not TradingFrequency.DAILY
                or experiment.asset_symbol != "SPY"
            ):
                raise InvalidExperimentConfigurationAppError(
                    "Paper trading supports only daily SPY Buy-and-Hold experiments.",
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
            execution_step = execution_step_repository.add(
                ExecutionStepModel(
                    experiment_id=experiment_id,
                    scheduled_for=now,
                    started_at=now,
                    completed_at=None,
                    status=ExecutionStepStatus.RUNNING,
                    trigger_type=TriggerType.MANUAL,
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

    def _run_step_artifacts(
        self,
        experiment_id: int,
        execution_step_id: int,
        broker_adapter: BrokerAdapter,
    ) -> PaperStepFailure | None:
        bar = self.market_data_provider.get_latest_bar("SPY")
        with self.session_factory() as session:
            now = _utcnow()
            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            portfolio = PortfolioRepository(session).get_by_experiment_id(experiment_id)
            execution_step = ExecutionStepRepository(session).get(execution_step_id)
            if experiment is None or portfolio is None or execution_step is None:
                raise RuntimeError(f"Experiment {experiment_id} is missing state.")

            market_data = MarketDataSnapshotRepository(session).add(
                MarketDataSnapshotModel(
                    execution_step_id=execution_step_id,
                    experiment_id=experiment_id,
                    timestamp=now,
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

            strategy_decision = self.strategy.decide(
                symbol="SPY",
                position_quantity=portfolio.position_quantity,
            )
            trading_decision = TradingDecisionRepository(session).add(
                TradingDecisionModel(
                    execution_step_id=execution_step_id,
                    experiment_id=experiment_id,
                    market_data_snapshot_id=market_data.id,
                    source_type=DecisionSourceType.STRATEGY,
                    source_name=self.strategy.source_name,
                    action=strategy_decision.action,
                    symbol=strategy_decision.symbol,
                    suggested_quantity=None,
                    suggested_notional=None,
                    confidence=Decimal("1.0000"),
                    reason=strategy_decision.reason,
                    raw_decision_json={"strategy": self.strategy.source_name},
                    created_at=now,
                )
            )
            session.flush()

            risk_result = self.risk_validator.evaluate(
                strategy_decision, portfolio, bar.adjusted_close
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

    def _run_broker_execution(
        self,
        *,
        experiment_id: int,
        execution_step_id: int,
        broker_adapter: BrokerAdapter,
        risk_result: RiskResult,
        risk_check_id: int,
        price: Decimal,
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
            event_type=SystemEventType.EXPERIMENT_FAILED,
            message="Experiment failed.",
            details_json=details,
            created_at=now,
        )
