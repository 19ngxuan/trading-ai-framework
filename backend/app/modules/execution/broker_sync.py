from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.domain.enums import (
    BrokerName,
    BrokerSyncStatus,
    OrderSide,
    OrderStatus,
)
from app.modules.broker.broker_adapter import BrokerAdapter, BrokerOrderResult
from app.modules.broker.errors import BrokerConfigurationError, BrokerProviderError
from app.modules.broker.factory import create_broker_adapter
from app.persistence.database import create_session_factory
from app.persistence.models import BrokerSyncLogModel, OrderModel, PortfolioModel, TradeModel
from app.persistence.repositories import (
    BrokerSyncLogRepository,
    OrderRepository,
    PortfolioRepository,
    TradeRepository,
)


@dataclass(frozen=True)
class BrokerOrderSyncResult:
    order_id: int
    broker_order_id: str
    sync_status: BrokerSyncStatus
    broker_status: str | None
    message: str


@dataclass(frozen=True)
class BrokerSyncRunResult:
    synced: list[BrokerOrderSyncResult]
    failed: list[BrokerOrderSyncResult]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PaperBrokerSyncService:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        broker_adapter: BrokerAdapter | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session_factory = session_factory or create_session_factory()
        self.settings = settings or get_settings()
        self.broker_adapter = broker_adapter

    def sync_open_orders(self) -> BrokerSyncRunResult:
        broker_adapter = self.broker_adapter or self._create_broker_adapter()
        with self.session_factory() as session:
            orders = OrderRepository(session).list_open_paper_orders()

        synced: list[BrokerOrderSyncResult] = []
        failed: list[BrokerOrderSyncResult] = []
        for order in orders:
            try:
                result = broker_adapter.get_order_status(order.broker_order_id or "")
                sync_result = self._persist_order_sync(order.id, result)
                if sync_result.sync_status is BrokerSyncStatus.FAILED:
                    failed.append(sync_result)
                else:
                    synced.append(sync_result)
            except BrokerProviderError as exc:
                failed.append(
                    self._persist_sync_failure(
                        order.id,
                        error_message=exc.message,
                        details=exc.details,
                    )
                )
        return BrokerSyncRunResult(synced=synced, failed=failed)

    def _create_broker_adapter(self) -> BrokerAdapter:
        try:
            return create_broker_adapter(self.settings)
        except BrokerConfigurationError as exc:
            raise BrokerProviderError(exc.message, details=exc.details) from exc

    def _persist_order_sync(
        self, order_id: int, broker_result: BrokerOrderResult
    ) -> BrokerOrderSyncResult:
        with self.session_factory() as session:
            now = _utcnow()
            order = session.get(OrderModel, order_id)
            if order is None:
                raise RuntimeError(f"Order {order_id} was not found.")
            portfolio = PortfolioRepository(session).get_by_experiment_id(
                order.experiment_id
            )
            if portfolio is None:
                raise RuntimeError(f"Portfolio for experiment {order.experiment_id} was not found.")

            mapped_status = _map_order_status(broker_result.status)
            if mapped_status is None:
                log = self._sync_log(
                    order=order,
                    portfolio=portfolio,
                    now=now,
                    sync_status=BrokerSyncStatus.FAILED,
                    details={
                        "syncType": "ORDER_STATUS_SYNC",
                        "brokerStatus": broker_result.status,
                        "brokerPayload": broker_result.raw,
                        "message": "Broker returned an unknown order status.",
                    },
                    error_message="Broker returned an unknown order status.",
                )
                BrokerSyncLogRepository(session).add(log)
                session.commit()
                return BrokerOrderSyncResult(
                    order_id=order.id,
                    broker_order_id=order.broker_order_id or "",
                    sync_status=BrokerSyncStatus.FAILED,
                    broker_status=broker_result.status,
                    message="Broker returned an unknown order status.",
                )

            previous_status = order.status
            order.status = mapped_status
            order.average_fill_price = broker_result.average_fill_price
            order.filled_at = broker_result.filled_at
            order.error_message = broker_result.error_message

            existing_filled_quantity = Decimal(
                str(TradeRepository(session).filled_quantity_by_order(order.id) or "0")
            )
            fill_delta = broker_result.filled_quantity - existing_filled_quantity
            if fill_delta > 0 and broker_result.average_fill_price is not None:
                trade = _apply_fill_delta_to_portfolio(
                    order=order,
                    portfolio=portfolio,
                    fill_quantity=fill_delta,
                    fill_price=broker_result.average_fill_price,
                    timestamp=broker_result.filled_at or now,
                    now=now,
                )
                session.add(trade)
                session.flush()

            BrokerSyncLogRepository(session).add(
                self._sync_log(
                    order=order,
                    portfolio=portfolio,
                    now=now,
                    sync_status=BrokerSyncStatus.SUCCESS,
                    details={
                        "syncType": "ORDER_STATUS_SYNC",
                        "orderId": order.id,
                        "brokerOrderId": order.broker_order_id,
                        "previousStatus": previous_status.value,
                        "brokerStatus": broker_result.status,
                        "mappedStatus": mapped_status.value,
                        "filledQuantity": str(broker_result.filled_quantity),
                        "brokerPayload": broker_result.raw,
                    },
                    error_message=None,
                )
            )
            session.commit()
            return BrokerOrderSyncResult(
                order_id=order.id,
                broker_order_id=order.broker_order_id or "",
                sync_status=BrokerSyncStatus.SUCCESS,
                broker_status=broker_result.status,
                message="Broker order status synced.",
            )

    def _persist_sync_failure(
        self, order_id: int, *, error_message: str, details: dict | None
    ) -> BrokerOrderSyncResult:
        with self.session_factory() as session:
            now = _utcnow()
            order = session.get(OrderModel, order_id)
            if order is None:
                raise RuntimeError(f"Order {order_id} was not found.")
            portfolio = PortfolioRepository(session).get_by_experiment_id(
                order.experiment_id
            )
            BrokerSyncLogRepository(session).add(
                self._sync_log(
                    order=order,
                    portfolio=portfolio,
                    now=now,
                    sync_status=BrokerSyncStatus.FAILED,
                    details={
                        "syncType": "ORDER_STATUS_SYNC",
                        "orderId": order.id,
                        "brokerOrderId": order.broker_order_id,
                        "errorDetails": details or {},
                    },
                    error_message=error_message,
                )
            )
            session.commit()
            return BrokerOrderSyncResult(
                order_id=order.id,
                broker_order_id=order.broker_order_id or "",
                sync_status=BrokerSyncStatus.FAILED,
                broker_status=None,
                message=error_message,
            )

    def _sync_log(
        self,
        *,
        order: OrderModel,
        portfolio: PortfolioModel | None,
        now: datetime,
        sync_status: BrokerSyncStatus,
        details: dict,
        error_message: str | None,
    ) -> BrokerSyncLogModel:
        return BrokerSyncLogModel(
            execution_step_id=order.execution_step_id,
            experiment_id=order.experiment_id,
            timestamp=now,
            broker_name=BrokerName.ALPACA,
            sync_status=sync_status,
            broker_cash=None,
            local_cash=portfolio.cash if portfolio is not None else None,
            broker_positions_json=None,
            local_positions_json=(
                {
                    "symbol": portfolio.position_symbol,
                    "quantity": str(portfolio.position_quantity),
                    "currentPositionValue": str(portfolio.current_position_value),
                }
                if portfolio is not None
                else None
            ),
            mismatch_details_json=details,
            error_message=error_message,
            created_at=now,
        )


def _map_order_status(status: str) -> OrderStatus | None:
    normalized = status.lower()
    if normalized == "filled":
        return OrderStatus.FILLED
    if normalized in {"accepted", "new", "pending_new", "partially_filled"}:
        return OrderStatus.SUBMITTED
    if normalized == "rejected":
        return OrderStatus.REJECTED
    if normalized in {"canceled", "cancelled", "expired"}:
        return OrderStatus.CANCELLED
    return None


def _apply_fill_delta_to_portfolio(
    *,
    order: OrderModel,
    portfolio: PortfolioModel,
    fill_quantity: Decimal,
    fill_price: Decimal,
    timestamp: datetime,
    now: datetime,
) -> TradeModel:
    fill_value = (fill_quantity * fill_price).quantize(Decimal("0.0001"))
    if order.side is OrderSide.BUY:
        portfolio.cash = (portfolio.cash - fill_value).quantize(Decimal("0.0001"))
        portfolio.position_symbol = order.symbol
        portfolio.position_quantity = (portfolio.position_quantity or Decimal("0")) + fill_quantity
    else:
        portfolio.cash = (portfolio.cash + fill_value).quantize(Decimal("0.0001"))
        remaining_quantity = (portfolio.position_quantity or Decimal("0")) - fill_quantity
        if remaining_quantity <= 0:
            portfolio.position_symbol = None
            portfolio.position_quantity = Decimal("0")
            portfolio.current_position_value = Decimal("0.0000")
        else:
            portfolio.position_symbol = order.symbol
            portfolio.position_quantity = remaining_quantity
    portfolio.current_price = fill_price
    portfolio.current_position_value = (
        (portfolio.position_quantity or Decimal("0")) * fill_price
    ).quantize(Decimal("0.0001"))
    portfolio.current_portfolio_value = (
        portfolio.cash + portfolio.current_position_value
    ).quantize(Decimal("0.0001"))
    portfolio.updated_at = now

    return TradeModel(
        execution_step_id=order.execution_step_id,
        experiment_id=order.experiment_id,
        order_id=order.id,
        timestamp=timestamp,
        symbol=order.symbol,
        side=order.side,
        quantity=fill_quantity,
        price=fill_price,
        order_value=fill_value,
        fee=Decimal("0"),
        portfolio_value_after_trade=portfolio.current_portfolio_value,
        created_at=now,
    )
