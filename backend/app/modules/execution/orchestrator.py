from datetime import datetime, time, timezone
from decimal import Decimal

from sqlalchemy.orm import Session, sessionmaker

from app.domain.enums import (
    DecisionSourceType,
    EventLevel,
    ExecutionStepStatus,
    ExperimentStatus,
    SystemEventType,
    TriggerType,
)
from app.modules.execution.metrics import BasicMetricCalculator
from app.modules.execution.risk import BuyAndHoldRiskValidator
from app.modules.execution.simulation_provider import SimulationExecutionProvider
from app.modules.market_data.csv_loader import DailyBar, SpyCsvLoader
from app.modules.strategies.buy_and_hold import BuyAndHoldStrategy
from app.persistence.database import create_session_factory
from app.persistence.models import (
    ExecutionStepModel,
    ExperimentModel,
    MarketDataSnapshotModel,
    MetricSnapshotModel,
    PortfolioSnapshotModel,
    RiskCheckModel,
    SystemEventLogModel,
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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _bar_timestamp(bar: DailyBar) -> datetime:
    return datetime.combine(bar.date, time.min)


class HistoricalBuyAndHoldOrchestrator:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        csv_loader: SpyCsvLoader | None = None,
    ) -> None:
        self.session_factory = session_factory or create_session_factory()
        self.csv_loader = csv_loader or SpyCsvLoader()
        self.strategy = BuyAndHoldStrategy()
        self.risk_validator = BuyAndHoldRiskValidator()
        self.execution_provider = SimulationExecutionProvider()
        self.metric_calculator = BasicMetricCalculator()

    def run(self, experiment_id: int) -> None:
        current_step_id: int | None = None
        try:
            experiment = self._load_experiment(experiment_id)
            bars = self.csv_loader.load_range(experiment.start_date, experiment.end_date)
            for bar in bars:
                current_step_id = self._create_running_step(experiment_id, bar)
                self._run_step(experiment_id, bar, current_step_id)
                current_step_id = None
            self._complete_experiment(experiment_id)
        except Exception:
            self._persist_failure(experiment_id, current_step_id)
            raise

    def _load_experiment(self, experiment_id: int) -> ExperimentModel:
        with self.session_factory() as session:
            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            if experiment is None:
                raise RuntimeError(f"Experiment {experiment_id} was not found.")
            session.expunge(experiment)
            return experiment

    def _create_running_step(self, experiment_id: int, bar: DailyBar) -> int:
        with self.session_factory() as session:
            now = _utcnow()
            timestamp = _bar_timestamp(bar)
            execution_step_repository = ExecutionStepRepository(session)
            execution_step = execution_step_repository.add(
                ExecutionStepModel(
                    experiment_id=experiment_id,
                    scheduled_for=timestamp,
                    started_at=now,
                    completed_at=None,
                    status=ExecutionStepStatus.RUNNING,
                    trigger_type=TriggerType.HISTORICAL,
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

    def _run_step(self, experiment_id: int, bar: DailyBar, execution_step_id: int) -> None:
        with self.session_factory() as session:
            now = _utcnow()
            timestamp = _bar_timestamp(bar)
            experiment_repository = ExperimentRepository(session)
            execution_step_repository = ExecutionStepRepository(session)
            market_data_repository = MarketDataSnapshotRepository(session)
            portfolio_repository = PortfolioRepository(session)
            trading_decision_repository = TradingDecisionRepository(session)
            risk_check_repository = RiskCheckRepository(session)
            portfolio_snapshot_repository = PortfolioSnapshotRepository(session)
            metric_snapshot_repository = MetricSnapshotRepository(session)
            trade_repository = TradeRepository(session)

            experiment = experiment_repository.get_by_id(experiment_id)
            portfolio = portfolio_repository.get_by_experiment_id(experiment_id)
            if experiment is None or portfolio is None:
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

            strategy_decision = self.strategy.decide(
                symbol="SPY",
                position_quantity=portfolio.position_quantity,
            )
            trading_decision = trading_decision_repository.add(
                TradingDecisionModel(
                    execution_step_id=execution_step.id,
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

            execution_result = self.execution_provider.execute_buy_if_applicable(
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

    def _complete_experiment(self, experiment_id: int) -> None:
        with self.session_factory() as session:
            now = _utcnow()
            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            if experiment is None:
                raise RuntimeError(f"Experiment {experiment_id} was not found.")
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
            session.commit()

    def _persist_failure(self, experiment_id: int, current_step_id: int | None) -> None:
        with self.session_factory() as session:
            now = _utcnow()
            if current_step_id is not None:
                step = ExecutionStepRepository(session).get(current_step_id)
                if step is not None:
                    step.status = ExecutionStepStatus.FAILED
                    step.completed_at = now
                    step.error_message = "Historical Buy-and-Hold simulation failed."

            experiment = ExperimentRepository(session).get_by_id(experiment_id)
            if experiment is not None:
                experiment.status = ExperimentStatus.FAILED
                experiment.updated_at = now
                SystemEventLogRepository(session).add(
                    SystemEventLogModel(
                        execution_step_id=current_step_id,
                        experiment_id=experiment_id,
                        timestamp=now,
                        level=EventLevel.ERROR,
                        event_type=SystemEventType.EXPERIMENT_FAILED,
                        message="Experiment failed.",
                        details_json={"experimentId": experiment_id},
                        created_at=now,
                    )
                )
            session.commit()
