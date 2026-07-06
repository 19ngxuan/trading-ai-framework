from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import (
    ExperimentStepAlreadyRunningAppError,
    InvalidExperimentConfigurationAppError,
)
from app.core.config import Settings
from app.domain.enums import (
    AgentMode,
    BrokerName,
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
    SystemEventType,
    TradeAction,
    TradingFrequency,
    TriggerType,
)
from app.modules.broker.broker_adapter import (
    BrokerAccountState,
    BrokerOrderResult,
    BrokerPosition,
)
from app.modules.broker.errors import BrokerProviderError
from app.modules.agents.fake_provider import FakeAgentProvider
from app.modules.agents.fake_pipeline_provider import FakePipelineProvider
from app.modules.agents.pipeline_agent import AgentDecisionPipeline
from app.modules.agents.single_agent import SingleAgent
from app.modules.execution.broker_sync import PaperBrokerSyncService
from app.modules.execution.paper_step_runner import PaperTradingStepRunner
from app.modules.strategies.agentic_ai_strategy import AgenticAIStrategy
from app.modules.market_data.errors import MarketDataUnavailableError
from app.modules.market_data.intraday_provider import IntradayBar
from app.modules.market_data.provider import DailyBar
from app.persistence.database import create_session_factory
from app.persistence.models import (
    AgentDecisionLogModel,
    ExecutionStepModel,
    BrokerSyncLogModel,
    ExperimentModel,
    MarketDataSnapshotModel,
    MetricSnapshotModel,
    OrderModel,
    PortfolioModel,
    PortfolioSnapshotModel,
    RiskCheckModel,
    StrategyConfigModel,
    SystemEventLogModel,
    TradeModel,
    TradingDecisionModel,
)


class FakeMarketDataProvider:
    def __init__(
        self,
        price: Decimal = Decimal("100.00"),
        range_bars: list[DailyBar] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.price = price
        self.range_bars = range_bars
        self.error = error
        self.latest_symbols: list[str] = []
        self.range_symbols: list[str | None] = []

    def load_range(self, *args, **kwargs) -> list[DailyBar]:
        self.range_symbols.append(kwargs.get("symbol"))
        if self.range_bars is not None:
            return self.range_bars
        return [self.get_latest_bar()]

    def get_latest_bar(self, symbol: str = "SPY") -> DailyBar:
        self.latest_symbols.append(symbol)
        if self.error is not None:
            raise self.error
        if self.range_bars is not None:
            return self.range_bars[-1]
        return DailyBar(
            date=date(2026, 1, 2),
            open=self.price,
            high=self.price,
            low=self.price,
            close=self.price,
            adjusted_close=self.price,
            volume=Decimal("1000"),
            raw={"provider": "fake", "symbol": symbol},
        )


class FakeIntradayProvider:
    def __init__(self, bars: list[IntradayBar]) -> None:
        self.bars = bars

    def load_range(self, *args, **kwargs) -> list[IntradayBar]:
        return self.bars

    def load_session_until(self, session_date, through_timestamp, *args, **kwargs):
        return [
            bar
            for bar in self.bars
            if bar.session_date == session_date and bar.timestamp <= through_timestamp
        ]


class FakeBrokerAdapter:
    def __init__(
        self,
        *,
        result: BrokerOrderResult | None = None,
        error: BrokerProviderError | None = None,
        on_place_order=None,
    ) -> None:
        self.result = result or _broker_result(status="filled", filled_quantity="100")
        self.error = error
        self.on_place_order = on_place_order
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
        if self.on_place_order is not None:
            self.on_place_order()
        if self.error is not None:
            raise self.error
        return self.result

    def get_order_status(self, broker_order_id: str) -> BrokerOrderResult:
        return self.result

    def get_account_state(self) -> BrokerAccountState:
        return BrokerAccountState(cash=None, status=None, raw={})

    def get_positions(self) -> list[BrokerPosition]:
        return []


def _broker_result(
    *,
    status: str,
    filled_quantity: str = "0",
    average_fill_price: str | None = "100.00",
    side: OrderSide = OrderSide.BUY,
    quantity: str = "100",
    symbol: str = "SPY",
) -> BrokerOrderResult:
    return BrokerOrderResult(
        broker_order_id=f"alpaca-{status}",
        status=status,
        symbol=symbol,
        side=side,
        quantity=Decimal(quantity),
        filled_quantity=Decimal(filled_quantity),
        average_fill_price=(
            Decimal(average_fill_price) if average_fill_price is not None else None
        ),
        submitted_at=datetime(2026, 1, 2, 12, 0, 0),
        filled_at=(
            datetime(2026, 1, 2, 12, 1, 0) if filled_quantity != "0" else None
        ),
        raw={"status": status},
    )


def _create_experiment(
    session: Session,
    *,
    status: ExperimentStatus = ExperimentStatus.RUNNING,
    mode: ExperimentMode = ExperimentMode.PAPER_TRADING,
    strategy_type: StrategyType = StrategyType.BUY_AND_HOLD,
    trading_frequency: TradingFrequency = TradingFrequency.DAILY,
    asset_symbol: str = "SPY",
    cash: Decimal = Decimal("10000.0000"),
    position_quantity: Decimal = Decimal("0"),
    moving_average_window: int | None = None,
    agent_mode=None,
    model_name: str | None = None,
    confidence_threshold: Decimal | None = None,
    parameters_json: dict | None = None,
) -> int:
    now = datetime(2026, 1, 1, 12, 0, 0)
    experiment = ExperimentModel(
        name="M9 Paper Trading",
        mode=mode,
        strategy_type=strategy_type,
        asset_symbol=asset_symbol,
        status=status,
        initial_capital=Decimal("10000.0000"),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
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
            moving_average_window=moving_average_window,
            agent_mode=agent_mode,
            model_name=model_name,
            confidence_threshold=confidence_threshold,
            parameters_json=parameters_json or {"riskConfig": {"fallbackAction": "HOLD"}},
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        PortfolioModel(
            experiment_id=experiment.id,
            cash=cash,
            position_symbol=asset_symbol if position_quantity > 0 else None,
            position_quantity=position_quantity,
            current_price=None,
            current_position_value=Decimal("0"),
            current_portfolio_value=cash,
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


def _runner(database_url: str, broker: FakeBrokerAdapter) -> PaperTradingStepRunner:
    return PaperTradingStepRunner(
        session_factory=create_session_factory(database_url),
        market_data_provider=FakeMarketDataProvider(),
        broker_adapter=broker,
    )


def _smoke_runner(database_url: str, broker: FakeBrokerAdapter) -> PaperTradingStepRunner:
    return PaperTradingStepRunner(
        session_factory=create_session_factory(database_url),
        market_data_provider=FakeMarketDataProvider(),
        broker_adapter=broker,
        settings=Settings(paper_trading_test_mode_enabled=True),
    )


def _runner_with_market_data(
    database_url: str,
    broker: FakeBrokerAdapter,
    market_data_provider: FakeMarketDataProvider,
) -> PaperTradingStepRunner:
    return PaperTradingStepRunner(
        session_factory=create_session_factory(database_url),
        market_data_provider=market_data_provider,
        broker_adapter=broker,
    )


def _runner_with_providers(
    database_url: str,
    broker: FakeBrokerAdapter,
    market_data_provider: FakeMarketDataProvider,
    intraday_provider: FakeIntradayProvider,
) -> PaperTradingStepRunner:
    return PaperTradingStepRunner(
        session_factory=create_session_factory(database_url),
        market_data_provider=market_data_provider,
        intraday_provider=intraday_provider,
        broker_adapter=broker,
    )


def _agent_runner(
    database_url: str,
    broker: FakeBrokerAdapter,
    market_data_provider: FakeMarketDataProvider,
) -> PaperTradingStepRunner:
    return PaperTradingStepRunner(
        session_factory=create_session_factory(database_url),
        market_data_provider=market_data_provider,
        broker_adapter=broker,
        agent_strategy=AgenticAIStrategy(
            agent=SingleAgent(provider=FakeAgentProvider())
        ),
    )


def _pipeline_agent_runner(
    database_url: str,
    broker: FakeBrokerAdapter,
    market_data_provider: FakeMarketDataProvider,
    intraday_provider: FakeIntradayProvider | None = None,
) -> PaperTradingStepRunner:
    return PaperTradingStepRunner(
        session_factory=create_session_factory(database_url),
        market_data_provider=market_data_provider,
        intraday_provider=intraday_provider,
        broker_adapter=broker,
        agent_strategy=AgenticAIStrategy(
            pipeline=AgentDecisionPipeline(
                provider=FakePipelineProvider(),
                market_data_provider=market_data_provider,
            )
        ),
    )


def _daily_bar(day: int, close: str) -> DailyBar:
    value = Decimal(close)
    return DailyBar(
        date=date(2026, 1, day),
        open=value,
        high=value,
        low=value,
        close=value,
        adjusted_close=value,
        volume=Decimal("1000"),
        raw={"provider": "fake", "date": f"2026-01-{day:02d}"},
    )


def _intraday_bar(hour: int, minute: int, close: str) -> IntradayBar:
    value = Decimal(close)
    timestamp = datetime(2026, 1, 2, hour, minute, 0)
    return IntradayBar(
        timestamp=timestamp,
        session_date=date(2026, 1, 2),
        open=value,
        high=value,
        low=value,
        close=value,
        volume=Decimal("1000"),
        raw={"provider": "fake_intraday", "timestamp": timestamp.isoformat()},
    )


def test_filled_buy_creates_paper_order_trade_and_updates_portfolio(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    broker = FakeBrokerAdapter(
        result=_broker_result(status="filled", filled_quantity="100")
    )
    result = _runner(database_url, broker).run_next_step(experiment_id)

    assert result.status is ExecutionStepStatus.COMPLETED
    assert len(broker.calls) == 1
    assert broker.calls[0]["clientOrderId"] == (
        f"experiment-{experiment_id}-step-{result.execution_step_id}-risk-1"
    )

    with session_factory() as session:
        step = session.get(ExecutionStepModel, result.execution_step_id)
        order = session.scalar(select(OrderModel).where(OrderModel.experiment_id == experiment_id))
        trade = session.scalar(select(TradeModel).where(TradeModel.experiment_id == experiment_id))
        portfolio = session.scalar(
            select(PortfolioModel).where(PortfolioModel.experiment_id == experiment_id)
        )
        assert step is not None
        assert step.status is ExecutionStepStatus.COMPLETED
        assert step.trigger_type is TriggerType.MANUAL
        assert order is not None
        assert order.mode is OrderMode.PAPER_BROKER
        assert order.broker_name is BrokerName.ALPACA
        assert order.status is OrderStatus.FILLED
        assert trade is not None
        assert trade.quantity == Decimal("100.00000000")
        assert portfolio is not None
        assert portfolio.cash == Decimal("0.0000")
        assert portfolio.position_symbol == "SPY"
        assert portfolio.position_quantity == Decimal("100.00000000")
        assert _count(session, MarketDataSnapshotModel, experiment_id) == 1
        assert _count(session, TradingDecisionModel, experiment_id) == 1
        assert _count(session, RiskCheckModel, experiment_id) == 1
        assert _count(session, PortfolioSnapshotModel, experiment_id) == 1
        assert _count(session, MetricSnapshotModel, experiment_id) == 1


def test_paper_buy_and_hold_uses_selected_symbol(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session, asset_symbol="AAPL")

    market_data_provider = FakeMarketDataProvider(price=Decimal("100"))
    broker = FakeBrokerAdapter(
        result=_broker_result(
            status="filled",
            filled_quantity="100",
            quantity="100",
            symbol="AAPL",
        )
    )
    result = _runner_with_market_data(
        database_url,
        broker,
        market_data_provider,
    ).run_next_step(experiment_id)

    assert result.status is ExecutionStepStatus.COMPLETED
    assert market_data_provider.latest_symbols == ["AAPL"]
    assert broker.calls[0]["symbol"] == "AAPL"
    with session_factory() as session:
        snapshot = session.scalar(
            select(MarketDataSnapshotModel).where(
                MarketDataSnapshotModel.experiment_id == experiment_id
            )
        )
        decision = session.scalar(
            select(TradingDecisionModel).where(
                TradingDecisionModel.experiment_id == experiment_id
            )
        )
        order = session.scalar(
            select(OrderModel).where(OrderModel.experiment_id == experiment_id)
        )
        trade = session.scalar(
            select(TradeModel).where(TradeModel.experiment_id == experiment_id)
        )
        portfolio = session.scalar(
            select(PortfolioModel).where(PortfolioModel.experiment_id == experiment_id)
        )
        assert snapshot is not None
        assert snapshot.symbol == "AAPL"
        assert decision is not None
        assert decision.symbol == "AAPL"
        assert order is not None
        assert order.symbol == "AAPL"
        assert trade is not None
        assert trade.symbol == "AAPL"
        assert portfolio is not None
        assert portfolio.position_symbol == "AAPL"


def test_paper_moving_average_uses_selected_symbol_for_lookback_and_order(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            strategy_type=StrategyType.MOVING_AVERAGE,
            asset_symbol="MSFT",
            moving_average_window=3,
        )

    market_data_provider = FakeMarketDataProvider(
        range_bars=[
            _daily_bar(1, "100"),
            _daily_bar(2, "100"),
            _daily_bar(3, "120"),
        ]
    )
    broker = FakeBrokerAdapter(
        result=_broker_result(
            status="filled",
            filled_quantity="83",
            average_fill_price="120.00",
            quantity="83",
            symbol="MSFT",
        )
    )

    result = _runner_with_market_data(
        database_url,
        broker,
        market_data_provider,
    ).run_next_step(experiment_id)

    assert result.status is ExecutionStepStatus.COMPLETED
    assert market_data_provider.latest_symbols == ["MSFT"]
    assert market_data_provider.range_symbols == ["MSFT"]
    assert broker.calls[0]["symbol"] == "MSFT"


def test_scheduled_paper_step_uses_scheduled_trigger_and_slot(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    scheduled_for = datetime(2026, 1, 2, 20, 55, 0)
    result = _runner(database_url, FakeBrokerAdapter()).run_next_step(
        experiment_id,
        trigger_type=TriggerType.SCHEDULED,
        scheduled_for=scheduled_for,
    )

    assert result.status is ExecutionStepStatus.COMPLETED
    with session_factory() as session:
        step = session.get(ExecutionStepModel, result.execution_step_id)
        assert step is not None
        assert step.trigger_type is TriggerType.SCHEDULED
        assert step.scheduled_for == scheduled_for


def test_duplicate_scheduled_paper_slot_is_rejected(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    scheduled_for = datetime(2026, 1, 2, 20, 55, 0)
    runner = _runner(database_url, FakeBrokerAdapter())
    runner.run_next_step(
        experiment_id,
        trigger_type=TriggerType.SCHEDULED,
        scheduled_for=scheduled_for,
    )

    with pytest.raises(ExperimentStepAlreadyRunningAppError):
        runner.run_next_step(
            experiment_id,
            trigger_type=TriggerType.SCHEDULED,
            scheduled_for=scheduled_for,
        )


def test_paper_buy_submitted_quantity_uses_default_cash_based_quantity(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    broker = FakeBrokerAdapter(
        result=_broker_result(status="accepted", filled_quantity="0")
    )
    result = _runner(database_url, broker).run_next_step(experiment_id)

    assert result.status is ExecutionStepStatus.COMPLETED
    assert len(broker.calls) == 1
    assert broker.calls[0]["quantity"] == Decimal("100")

    with session_factory() as session:
        risk_check = session.scalar(
            select(RiskCheckModel).where(RiskCheckModel.experiment_id == experiment_id)
        )
        assert risk_check is not None
        assert risk_check.final_quantity == Decimal("100.00000000")
        assert risk_check.rules_triggered_json["reason"] == "DEFAULT_WHOLE_SHARE_BUY"


def test_hold_creates_no_broker_call_order_or_trade(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            cash=Decimal("0.0000"),
            position_quantity=Decimal("10"),
        )

    broker = FakeBrokerAdapter()
    result = _runner(database_url, broker).run_next_step(experiment_id)

    assert result.status is ExecutionStepStatus.COMPLETED
    assert broker.calls == []
    with session_factory() as session:
        assert _count(session, OrderModel, experiment_id) == 0
        assert _count(session, TradeModel, experiment_id) == 0
        assert _count(session, RiskCheckModel, experiment_id) == 1


def test_submitted_unfilled_order_completes_without_trade(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    broker = FakeBrokerAdapter(
        result=_broker_result(
            status="accepted",
            filled_quantity="0",
            average_fill_price=None,
        )
    )
    result = _runner(database_url, broker).run_next_step(experiment_id)

    assert result.status is ExecutionStepStatus.COMPLETED
    with session_factory() as session:
        order = session.scalar(select(OrderModel).where(OrderModel.experiment_id == experiment_id))
        assert order is not None
        assert order.status is OrderStatus.SUBMITTED
        assert _count(session, TradeModel, experiment_id) == 0


def test_broker_sync_filled_submitted_order_creates_trade_and_updates_portfolio(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    submit_broker = FakeBrokerAdapter(
        result=_broker_result(
            status="accepted",
            filled_quantity="0",
            average_fill_price=None,
        )
    )
    _runner(database_url, submit_broker).run_next_step(experiment_id)

    sync_broker = FakeBrokerAdapter(
        result=_broker_result(status="filled", filled_quantity="100")
    )
    result = PaperBrokerSyncService(
        session_factory=session_factory,
        broker_adapter=sync_broker,
    ).sync_open_orders()

    assert len(result.synced) == 1
    assert result.failed == []
    with session_factory() as session:
        order = session.scalar(select(OrderModel).where(OrderModel.experiment_id == experiment_id))
        trade = session.scalar(select(TradeModel).where(TradeModel.experiment_id == experiment_id))
        portfolio = session.scalar(
            select(PortfolioModel).where(PortfolioModel.experiment_id == experiment_id)
        )
        sync_log = session.scalar(
            select(BrokerSyncLogModel).where(
                BrokerSyncLogModel.experiment_id == experiment_id
            )
        )
        assert order is not None
        assert order.status is OrderStatus.FILLED
        assert trade is not None
        assert trade.quantity == Decimal("100.00000000")
        assert portfolio is not None
        assert portfolio.cash == Decimal("0.0000")
        assert portfolio.position_quantity == Decimal("100.00000000")
        assert sync_log is not None
        assert sync_log.sync_status.value == "SUCCESS"


def test_broker_sync_partial_fill_only_creates_delta_trades(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    _runner(
        database_url,
        FakeBrokerAdapter(
            result=_broker_result(
                status="accepted",
                filled_quantity="0",
                average_fill_price=None,
            )
        ),
    ).run_next_step(experiment_id)

    sync_broker = FakeBrokerAdapter(
        result=_broker_result(status="partially_filled", filled_quantity="25")
    )
    service = PaperBrokerSyncService(
        session_factory=session_factory,
        broker_adapter=sync_broker,
    )
    service.sync_open_orders()
    service.sync_open_orders()

    with session_factory() as session:
        order = session.scalar(select(OrderModel).where(OrderModel.experiment_id == experiment_id))
        trades = list(
            session.scalars(
                select(TradeModel).where(TradeModel.experiment_id == experiment_id)
            )
        )
        portfolio = session.scalar(
            select(PortfolioModel).where(PortfolioModel.experiment_id == experiment_id)
        )
        assert order is not None
        assert order.status is OrderStatus.SUBMITTED
        assert len(trades) == 1
        assert trades[0].quantity == Decimal("25.00000000")
        assert portfolio is not None
        assert portfolio.cash == Decimal("7500.0000")
        assert portfolio.position_quantity == Decimal("25.00000000")


def test_broker_sync_unknown_status_records_failure_without_failing_experiment(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    _runner(
        database_url,
        FakeBrokerAdapter(
            result=_broker_result(
                status="accepted",
                filled_quantity="0",
                average_fill_price=None,
            )
        ),
    ).run_next_step(experiment_id)

    result = PaperBrokerSyncService(
        session_factory=session_factory,
        broker_adapter=FakeBrokerAdapter(result=_broker_result(status="mystery")),
    ).sync_open_orders()

    assert result.synced == []
    assert len(result.failed) == 1
    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        sync_log = session.scalar(
            select(BrokerSyncLogModel).where(
                BrokerSyncLogModel.experiment_id == experiment_id
            )
        )
        assert experiment is not None
        assert experiment.status is ExperimentStatus.RUNNING
        assert sync_log is not None
        assert sync_log.sync_status.value == "FAILED"


def test_partial_fill_maps_to_submitted_and_updates_for_filled_quantity(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    broker = FakeBrokerAdapter(
        result=_broker_result(status="partially_filled", filled_quantity="25")
    )
    result = _runner(database_url, broker).run_next_step(experiment_id)

    assert result.status is ExecutionStepStatus.COMPLETED
    with session_factory() as session:
        order = session.scalar(select(OrderModel).where(OrderModel.experiment_id == experiment_id))
        trade = session.scalar(select(TradeModel).where(TradeModel.experiment_id == experiment_id))
        portfolio = session.scalar(
            select(PortfolioModel).where(PortfolioModel.experiment_id == experiment_id)
        )
        assert order is not None
        assert order.status is OrderStatus.SUBMITTED
        assert trade is not None
        assert trade.quantity == Decimal("25.00000000")
        assert portfolio is not None
        assert portfolio.cash == Decimal("7500.0000")
        assert portfolio.position_quantity == Decimal("25.00000000")


def test_rejected_order_fails_step_and_experiment(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    broker = FakeBrokerAdapter(
        result=_broker_result(
            status="rejected",
            filled_quantity="0",
            average_fill_price=None,
        )
    )
    result = _runner(database_url, broker).run_next_step(experiment_id)

    assert result.status is ExecutionStepStatus.FAILED
    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        step = session.get(ExecutionStepModel, result.execution_step_id)
        order = session.scalar(select(OrderModel).where(OrderModel.experiment_id == experiment_id))
        event = session.scalar(
            select(SystemEventLogModel).where(
                SystemEventLogModel.experiment_id == experiment_id,
                SystemEventLogModel.event_type == SystemEventType.EXPERIMENT_FAILED,
            )
        )
        assert experiment is not None
        assert experiment.status is ExperimentStatus.FAILED
        assert step is not None
        assert step.status is ExecutionStepStatus.FAILED
        assert order is not None
        assert order.status is OrderStatus.REJECTED
        assert _count(session, TradeModel, experiment_id) == 0
        assert event is not None
        assert event.details_json["errorCode"] == "ORDER_REJECTED"
        assert event.details_json["provider"] == "alpaca"


def test_broker_provider_error_fails_step_but_keeps_experiment_running(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    broker = FakeBrokerAdapter(
        error=BrokerProviderError("network failed", details={"statusCode": 500})
    )
    with pytest.raises(BrokerProviderError):
        _runner(database_url, broker).run_next_step(experiment_id)

    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        step = session.scalar(
            select(ExecutionStepModel).where(
                ExecutionStepModel.experiment_id == experiment_id
            )
        )
        event = session.scalar(
            select(SystemEventLogModel).where(
                SystemEventLogModel.experiment_id == experiment_id,
                SystemEventLogModel.event_type == SystemEventType.ORDER_FAILED,
            )
        )
        assert experiment is not None
        assert experiment.status is ExperimentStatus.RUNNING
        assert step is not None
        assert step.status is ExecutionStepStatus.FAILED
        assert event is not None
        assert event.details_json["errorCode"] == "BROKER_PROVIDER_ERROR"
        assert event.details_json["providerDetails"] == {"statusCode": 500}
        assert _count(session, OrderModel, experiment_id) == 0
        assert _count(session, BrokerSyncLogModel, experiment_id) == 1


def test_market_data_error_fails_step_but_keeps_experiment_running(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    with pytest.raises(MarketDataUnavailableError):
        _runner_with_market_data(
            database_url,
            FakeBrokerAdapter(),
            FakeMarketDataProvider(
                error=MarketDataUnavailableError(
                    "No latest bar.",
                    details={"symbol": "SPY"},
                )
            ),
        ).run_next_step(experiment_id)

    with session_factory() as session:
        experiment = session.get(ExperimentModel, experiment_id)
        step = session.scalar(
            select(ExecutionStepModel).where(
                ExecutionStepModel.experiment_id == experiment_id
            )
        )
        event = session.scalar(
            select(SystemEventLogModel).where(
                SystemEventLogModel.experiment_id == experiment_id,
                SystemEventLogModel.event_type == SystemEventType.MARKET_DATA_MISSING,
            )
        )
        assert experiment is not None
        assert experiment.status is ExperimentStatus.RUNNING
        assert step is not None
        assert step.status is ExecutionStepStatus.FAILED
        assert event is not None
        assert event.details_json["errorCode"] == "MARKET_DATA_MISSING"
        assert _count(session, OrderModel, experiment_id) == 0
        assert _count(session, TradeModel, experiment_id) == 0


def test_risk_check_is_committed_before_broker_submission(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)

    def assert_committed_risk_check() -> None:
        with session_factory() as check_session:
            assert _count(check_session, RiskCheckModel, experiment_id) == 1

    broker = FakeBrokerAdapter(on_place_order=assert_committed_risk_check)
    result = _runner(database_url, broker).run_next_step(experiment_id)

    assert result.status is ExecutionStepStatus.COMPLETED


def test_existing_running_step_is_rejected(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session)
        session.add(
            ExecutionStepModel(
                experiment_id=experiment_id,
                scheduled_for=datetime(2026, 1, 2, 12, 0, 0),
                started_at=datetime(2026, 1, 2, 12, 0, 0),
                completed_at=None,
                status=ExecutionStepStatus.RUNNING,
                trigger_type=TriggerType.MANUAL,
                sequence_number=1,
                error_message=None,
                created_at=datetime(2026, 1, 2, 12, 0, 0),
            )
        )
        session.commit()

    with pytest.raises(ExperimentStepAlreadyRunningAppError):
        _runner(database_url, FakeBrokerAdapter()).run_next_step(experiment_id)


@pytest.mark.parametrize(
    "overrides",
    [
        {"mode": ExperimentMode.HISTORICAL_SIMULATION},
        {"strategy_type": StrategyType.BUY_AND_HOLD, "trading_frequency": TradingFrequency.HOURLY},
        {"trading_frequency": TradingFrequency.WEEKLY},
        {"asset_symbol": "QQQ"},
    ],
)
def test_unsupported_configuration_is_rejected(
    database_url: str, overrides: dict
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(session, **overrides)

    with pytest.raises(InvalidExperimentConfigurationAppError):
        _runner(database_url, FakeBrokerAdapter()).run_next_step(experiment_id)


def test_smoke_test_manual_run_next_step_is_rejected(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            strategy_type=StrategyType.PAPER_TRADING_SMOKE_TEST,
            trading_frequency=TradingFrequency.TEST_1_MIN,
        )

    with pytest.raises(InvalidExperimentConfigurationAppError):
        _smoke_runner(database_url, FakeBrokerAdapter()).run_next_step(
            experiment_id,
            trigger_type=TriggerType.MANUAL,
        )


def test_smoke_test_scheduled_first_slot_buys_one_share(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            strategy_type=StrategyType.PAPER_TRADING_SMOKE_TEST,
            trading_frequency=TradingFrequency.TEST_1_MIN,
        )

    broker = FakeBrokerAdapter(
        result=_broker_result(status="filled", filled_quantity="1", quantity="1")
    )
    result = _smoke_runner(database_url, broker).run_next_step(
        experiment_id,
        trigger_type=TriggerType.SCHEDULED,
        scheduled_for=datetime(2026, 1, 2, 15, 31),
    )

    assert result.status is ExecutionStepStatus.COMPLETED
    assert broker.calls[0]["quantity"] == Decimal("1")
    assert broker.calls[0]["side"] is OrderSide.BUY

    with session_factory() as session:
        order = session.scalar(
            select(OrderModel).where(OrderModel.experiment_id == experiment_id)
        )
        decision = session.scalar(
            select(TradingDecisionModel).where(
                TradingDecisionModel.experiment_id == experiment_id
            )
        )
        risk = session.scalar(
            select(RiskCheckModel).where(RiskCheckModel.experiment_id == experiment_id)
        )
        assert order is not None
        assert order.quantity == Decimal("1.00000000")
        assert decision is not None
        assert decision.source_name == "PaperTradingSmokeTestStrategy"
        assert decision.raw_decision_json["diagnosticOnly"] is True
        assert risk is not None
        assert risk.final_quantity == Decimal("1.00000000")


def test_smoke_test_scheduled_next_slot_sells_existing_position(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            strategy_type=StrategyType.PAPER_TRADING_SMOKE_TEST,
            trading_frequency=TradingFrequency.TEST_1_MIN,
            cash=Decimal("9900.0000"),
            position_quantity=Decimal("1"),
        )

    broker = FakeBrokerAdapter(
        result=_broker_result(
            status="filled",
            filled_quantity="1",
            side=OrderSide.SELL,
            quantity="1",
        )
    )
    result = _smoke_runner(database_url, broker).run_next_step(
        experiment_id,
        trigger_type=TriggerType.SCHEDULED,
        scheduled_for=datetime(2026, 1, 2, 15, 32),
    )

    assert result.status is ExecutionStepStatus.COMPLETED
    assert broker.calls[0]["quantity"] == Decimal("1")
    assert broker.calls[0]["side"] is OrderSide.SELL

    with session_factory() as session:
        portfolio = session.scalar(
            select(PortfolioModel).where(PortfolioModel.experiment_id == experiment_id)
        )
        assert portfolio is not None
        assert portfolio.position_quantity == Decimal("0")
        assert portfolio.position_symbol is None


def test_smoke_test_duplicate_scheduled_slot_is_rejected(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    scheduled_for = datetime(2026, 1, 2, 15, 33)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            strategy_type=StrategyType.PAPER_TRADING_SMOKE_TEST,
            trading_frequency=TradingFrequency.TEST_1_MIN,
        )
        session.add(
            ExecutionStepModel(
                experiment_id=experiment_id,
                scheduled_for=scheduled_for,
                started_at=scheduled_for,
                completed_at=scheduled_for,
                status=ExecutionStepStatus.COMPLETED,
                trigger_type=TriggerType.SCHEDULED,
                sequence_number=1,
                error_message=None,
                created_at=scheduled_for,
            )
        )
        session.commit()

    broker = FakeBrokerAdapter()
    with pytest.raises(ExperimentStepAlreadyRunningAppError):
        _smoke_runner(database_url, broker).run_next_step(
            experiment_id,
            trigger_type=TriggerType.SCHEDULED,
            scheduled_for=scheduled_for,
        )
    assert broker.calls == []


def test_moving_average_manual_paper_step_can_buy_for_debugging(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            strategy_type=StrategyType.MOVING_AVERAGE,
            moving_average_window=3,
        )

    bars = [_daily_bar(1, "100"), _daily_bar(2, "101"), _daily_bar(3, "110")]
    broker = FakeBrokerAdapter(
        result=_broker_result(status="filled", filled_quantity="90", quantity="90")
    )
    runner = _runner_with_market_data(
        database_url,
        broker,
        FakeMarketDataProvider(price=Decimal("110"), range_bars=bars),
    )

    result = runner.run_next_step(experiment_id, trigger_type=TriggerType.MANUAL)

    assert result.status is ExecutionStepStatus.COMPLETED
    assert broker.calls[0]["side"] is OrderSide.BUY
    with session_factory() as session:
        decision = session.scalar(
            select(TradingDecisionModel).where(
                TradingDecisionModel.experiment_id == experiment_id
            )
        )
        snapshot = session.scalar(
            select(MarketDataSnapshotModel).where(
                MarketDataSnapshotModel.experiment_id == experiment_id
            )
        )
        assert decision is not None
        assert decision.source_name == "MovingAverageStrategy"
        assert decision.raw_decision_json["movingAverageWindow"] == 3
        assert snapshot is not None
        assert snapshot.moving_average == Decimal("103.6667")


def test_moving_average_insufficient_lookback_holds_without_broker_call(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            strategy_type=StrategyType.MOVING_AVERAGE,
            moving_average_window=3,
        )

    broker = FakeBrokerAdapter()
    runner = _runner_with_market_data(
        database_url,
        broker,
        FakeMarketDataProvider(
            price=Decimal("110"),
            range_bars=[_daily_bar(2, "101"), _daily_bar(3, "110")],
        ),
    )

    result = runner.run_next_step(experiment_id, trigger_type=TriggerType.SCHEDULED)

    assert result.status is ExecutionStepStatus.COMPLETED
    assert broker.calls == []
    with session_factory() as session:
        decision = session.scalar(
            select(TradingDecisionModel).where(
                TradingDecisionModel.experiment_id == experiment_id
            )
        )
        assert decision is not None
        assert decision.action.value == "HOLD"
        assert (
            decision.raw_decision_json["reasonCode"]
            == "INSUFFICIENT_MOVING_AVERAGE_LOOKBACK"
        )


def test_scheduled_orb_paper_breakout_buys_after_risk_check(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            strategy_type=StrategyType.OPENING_RANGE_BREAKOUT,
            trading_frequency=TradingFrequency.INTRADAY_5_MIN,
        )

    bars = [
        _intraday_bar(9, 30, "100"),
        _intraday_bar(9, 35, "100"),
        _intraday_bar(9, 40, "100"),
        _intraday_bar(9, 45, "100"),
        _intraday_bar(9, 50, "100"),
        _intraday_bar(9, 55, "100"),
        _intraday_bar(10, 0, "110"),
    ]
    broker = FakeBrokerAdapter(
        result=_broker_result(status="filled", filled_quantity="90", quantity="90")
    )
    result = _runner_with_providers(
        database_url,
        broker,
        FakeMarketDataProvider(),
        FakeIntradayProvider(bars),
    ).run_next_step(
        experiment_id,
        trigger_type=TriggerType.SCHEDULED,
        scheduled_for=datetime(2026, 1, 2, 10, 0),
    )

    assert result.status is ExecutionStepStatus.COMPLETED
    assert broker.calls[0]["side"] is OrderSide.BUY
    with session_factory() as session:
        decision = session.scalar(
            select(TradingDecisionModel).where(
                TradingDecisionModel.experiment_id == experiment_id
            )
        )
        risk = session.scalar(
            select(RiskCheckModel).where(RiskCheckModel.experiment_id == experiment_id)
        )
        assert decision is not None
        assert decision.source_name == "OpeningRangeBreakoutStrategy"
        assert decision.raw_decision_json["openingRangeComplete"] is True
        assert decision.raw_decision_json["breakoutDirection"] == "UP"
        assert risk is not None
        assert risk.trading_decision_id == decision.id


def test_orb_paper_manual_run_next_step_is_rejected(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            strategy_type=StrategyType.OPENING_RANGE_BREAKOUT,
            trading_frequency=TradingFrequency.INTRADAY_5_MIN,
        )

    with pytest.raises(InvalidExperimentConfigurationAppError):
        _runner_with_providers(
            database_url,
            FakeBrokerAdapter(),
            FakeMarketDataProvider(),
            FakeIntradayProvider([]),
        ).run_next_step(experiment_id, trigger_type=TriggerType.MANUAL)


def test_agentic_ai_paper_single_agent_buy_creates_agent_log_and_order(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            strategy_type=StrategyType.AGENTIC_AI,
            asset_symbol="NVDA",
            agent_mode=AgentMode.SINGLE_AGENT,
            model_name="meta-llama/Llama-3.3-70B-Instruct",
            parameters_json={
                "riskConfig": {"fallbackAction": "HOLD"},
                "fakeAgent": {
                    "output": {
                        "action": "BUY",
                        "confidence": 0.9,
                        "rationale": "Paper agent test BUY.",
                    }
                },
            },
        )

    broker = FakeBrokerAdapter(
        result=_broker_result(
            status="filled",
            filled_quantity="100",
            quantity="100",
            symbol="NVDA",
        )
    )
    market_data_provider = FakeMarketDataProvider(price=Decimal("100"))
    result = _agent_runner(
        database_url,
        broker,
        market_data_provider,
    ).run_next_step(experiment_id, trigger_type=TriggerType.MANUAL)

    assert result.status is ExecutionStepStatus.COMPLETED
    assert market_data_provider.latest_symbols == ["NVDA"]
    assert broker.calls[0]["symbol"] == "NVDA"
    assert broker.calls[0]["side"] is OrderSide.BUY
    with session_factory() as session:
        decision = session.scalar(
            select(TradingDecisionModel).where(
                TradingDecisionModel.experiment_id == experiment_id
            )
        )
        agent_log_count = _count(session, AgentDecisionLogModel, experiment_id)
        risk = session.scalar(
            select(RiskCheckModel).where(RiskCheckModel.experiment_id == experiment_id)
        )
        assert decision is not None
        assert decision.source_type is DecisionSourceType.AGENT
        assert decision.symbol == "NVDA"
        assert decision.action is TradeAction.BUY
        assert agent_log_count == 1
        assert risk is not None
        assert risk.trading_decision_id == decision.id


def test_agentic_ai_paper_low_confidence_holds_without_broker_call(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            strategy_type=StrategyType.AGENTIC_AI,
            agent_mode=AgentMode.SINGLE_AGENT,
            model_name="meta-llama/Llama-3.3-70B-Instruct",
            confidence_threshold=Decimal("0.8000"),
            parameters_json={
                "riskConfig": {"fallbackAction": "HOLD"},
                "fakeAgent": {
                    "output": {
                        "action": "BUY",
                        "confidence": 0.2,
                        "rationale": "Low confidence BUY.",
                    }
                },
            },
        )

    broker = FakeBrokerAdapter()
    result = _agent_runner(
        database_url,
        broker,
        FakeMarketDataProvider(price=Decimal("100")),
    ).run_next_step(experiment_id, trigger_type=TriggerType.SCHEDULED)

    assert result.status is ExecutionStepStatus.COMPLETED
    assert broker.calls == []
    with session_factory() as session:
        decision = session.scalar(
            select(TradingDecisionModel).where(
                TradingDecisionModel.experiment_id == experiment_id
            )
        )
        assert decision is not None
        assert decision.action is TradeAction.HOLD
        assert decision.raw_decision_json["fallbackReason"] == "CONFIDENCE_BELOW_THRESHOLD"


def test_agentic_ai_pipeline_paper_creates_six_agent_logs(database_url: str) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            strategy_type=StrategyType.AGENTIC_AI,
            agent_mode=AgentMode.PIPELINE,
            model_name="meta-llama/Llama-3.3-70B-Instruct",
            parameters_json={
                "riskConfig": {"fallbackAction": "HOLD"},
                "fakePipeline": {
                    "marketAnalystOutput": {
                        "marketBias": "BULLISH",
                        "confidence": 0.8,
                        "rationale": "Bullish context.",
                    },
                    "tradingDecisionOutput": {
                        "action": "BUY",
                        "confidence": 0.9,
                        "rationale": "Pipeline buy.",
                    },
                    "riskManagerOutput": {
                        "verdict": "APPROVE",
                        "confidence": 0.9,
                        "rationale": "Approved.",
                    },
                },
            },
        )

    broker = FakeBrokerAdapter(
        result=_broker_result(status="filled", filled_quantity="100", quantity="100")
    )
    result = _pipeline_agent_runner(
        database_url,
        broker,
        FakeMarketDataProvider(price=Decimal("100")),
    ).run_next_step(experiment_id, trigger_type=TriggerType.MANUAL)

    assert result.status is ExecutionStepStatus.COMPLETED
    assert broker.calls[0]["side"] is OrderSide.BUY
    with session_factory() as session:
        assert _count(session, AgentDecisionLogModel, experiment_id) == 6


def test_agentic_ai_hourly_single_agent_uses_completed_hour_bar(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            strategy_type=StrategyType.AGENTIC_AI,
            trading_frequency=TradingFrequency.HOURLY,
            agent_mode=AgentMode.SINGLE_AGENT,
            model_name="meta-llama/Llama-3.3-70B-Instruct",
            parameters_json={
                "riskConfig": {"fallbackAction": "HOLD"},
                "fakeAgent": {
                    "output": {
                        "action": "BUY",
                        "confidence": 0.9,
                        "rationale": "Hourly BUY.",
                    }
                },
            },
        )

    bars = [_intraday_bar(9, minute, "100") for minute in (30, 35, 40, 45, 50, 55)]
    bars += [_intraday_bar(10, minute, "101") for minute in (0, 5, 10, 15, 20, 25)]
    broker = FakeBrokerAdapter(
        result=_broker_result(status="filled", filled_quantity="99", quantity="99")
    )
    result = _agent_runner(
        database_url,
        broker,
        FakeMarketDataProvider(price=Decimal("100")),
    )
    result.intraday_provider = FakeIntradayProvider(bars)
    step_result = result.run_next_step(
        experiment_id,
        trigger_type=TriggerType.SCHEDULED,
        scheduled_for=datetime(2026, 1, 2, 14, 30),
    )

    assert step_result.status is ExecutionStepStatus.COMPLETED
    with session_factory() as session:
        snapshot = session.scalar(
            select(MarketDataSnapshotModel).where(
                MarketDataSnapshotModel.experiment_id == experiment_id
            )
        )
        assert _count(session, AgentDecisionLogModel, experiment_id) == 1
        assert snapshot is not None
        assert snapshot.close == Decimal("101")
        assert snapshot.volume == Decimal("12000")


def test_agentic_ai_hourly_pipeline_uses_completed_hour_bar(
    database_url: str,
) -> None:
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session,
            strategy_type=StrategyType.AGENTIC_AI,
            trading_frequency=TradingFrequency.HOURLY,
            agent_mode=AgentMode.PIPELINE,
            model_name="meta-llama/Llama-3.3-70B-Instruct",
            parameters_json={
                "riskConfig": {"fallbackAction": "HOLD"},
                "fakePipeline": {
                    "marketAnalystOutput": {
                        "marketBias": "BULLISH",
                        "confidence": 0.8,
                        "rationale": "Bullish context.",
                    },
                    "tradingDecisionOutput": {
                        "action": "BUY",
                        "confidence": 0.9,
                        "rationale": "Pipeline buy.",
                    },
                    "riskManagerOutput": {
                        "verdict": "APPROVE",
                        "confidence": 0.9,
                        "rationale": "Approved.",
                    },
                },
            },
        )

    bars = [_intraday_bar(9, minute, "100") for minute in (30, 35, 40, 45, 50, 55)]
    bars += [_intraday_bar(10, minute, "102") for minute in (0, 5, 10, 15, 20, 25)]
    broker = FakeBrokerAdapter(
        result=_broker_result(status="filled", filled_quantity="98", quantity="98")
    )
    runner = _pipeline_agent_runner(
        database_url,
        broker,
        FakeMarketDataProvider(price=Decimal("100")),
        FakeIntradayProvider(bars),
    )

    step_result = runner.run_next_step(
        experiment_id,
        trigger_type=TriggerType.SCHEDULED,
        scheduled_for=datetime(2026, 1, 2, 14, 30),
    )

    assert step_result.status is ExecutionStepStatus.COMPLETED
    with session_factory() as session:
        assert _count(session, AgentDecisionLogModel, experiment_id) == 6
