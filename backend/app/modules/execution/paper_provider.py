from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domain.enums import (
    BrokerName,
    FinalAction,
    OrderMode,
    OrderSide,
    OrderStatus,
    OrderType,
)
from app.modules.broker.broker_adapter import BrokerAdapter, BrokerOrderResult
from app.modules.execution.risk import RiskResult
from app.persistence.models import OrderModel, PortfolioModel, TradeModel


@dataclass(frozen=True)
class PaperExecutionResult:
    order: OrderModel | None
    trade: TradeModel | None
    broker_result: BrokerOrderResult | None
    rejected: bool = False


class PaperExecutionProvider:
    def __init__(self, broker_adapter: BrokerAdapter) -> None:
        self.broker_adapter = broker_adapter

    def execute_if_applicable(
        self,
        *,
        session: Session,
        risk_result: RiskResult,
        portfolio: PortfolioModel,
        experiment_id: int,
        execution_step_id: int,
        risk_check_id: int,
        symbol: str,
        timestamp: datetime,
        now: datetime,
    ) -> PaperExecutionResult:
        if (
            not risk_result.approved
            or risk_result.final_action is FinalAction.HOLD
            or risk_result.final_quantity is None
            or risk_result.final_quantity <= 0
        ):
            return PaperExecutionResult(order=None, trade=None, broker_result=None)

        existing_order = session.scalar(
            select(OrderModel)
            .where(
                or_(
                    OrderModel.execution_step_id == execution_step_id,
                    OrderModel.risk_check_id == risk_check_id,
                )
            )
            .limit(1)
        )
        if existing_order is not None:
            return PaperExecutionResult(
                order=existing_order,
                trade=None,
                broker_result=None,
                rejected=existing_order.status is OrderStatus.REJECTED,
            )

        side = _side_for_action(risk_result.final_action)
        broker_result = self.broker_adapter.place_order(
            symbol=symbol,
            side=side,
            quantity=risk_result.final_quantity,
            order_type=OrderType.MARKET,
            client_order_id=(
                f"experiment-{experiment_id}-step-{execution_step_id}-risk-{risk_check_id}"
            ),
        )
        order_status = _map_order_status(broker_result.status)
        order = OrderModel(
            execution_step_id=execution_step_id,
            experiment_id=experiment_id,
            risk_check_id=risk_check_id,
            mode=OrderMode.PAPER_BROKER,
            broker_name=BrokerName.ALPACA,
            broker_order_id=broker_result.broker_order_id,
            symbol=broker_result.symbol,
            side=broker_result.side,
            quantity=broker_result.quantity,
            order_type=OrderType.MARKET,
            status=order_status,
            submitted_at=broker_result.submitted_at or timestamp,
            filled_at=broker_result.filled_at,
            average_fill_price=broker_result.average_fill_price,
            error_message=broker_result.error_message,
            created_at=now,
        )

        trade = None
        if (
            broker_result.filled_quantity > 0
            and broker_result.average_fill_price is not None
        ):
            trade = _apply_fill_to_portfolio(
                broker_result=broker_result,
                portfolio=portfolio,
                experiment_id=experiment_id,
                execution_step_id=execution_step_id,
                timestamp=timestamp,
                now=now,
            )

        return PaperExecutionResult(
            order=order,
            trade=trade,
            broker_result=broker_result,
            rejected=order_status is OrderStatus.REJECTED,
        )


def _side_for_action(action: FinalAction) -> OrderSide:
    if action is FinalAction.BUY:
        return OrderSide.BUY
    if action is FinalAction.SELL:
        return OrderSide.SELL
    raise ValueError(f"Unsupported paper trading action: {action.value}")


def _map_order_status(status: str) -> OrderStatus:
    normalized = status.lower()
    if normalized == "filled":
        return OrderStatus.FILLED
    if normalized in {"accepted", "new", "pending_new", "partially_filled"}:
        return OrderStatus.SUBMITTED
    if normalized == "rejected":
        return OrderStatus.REJECTED
    if normalized in {"canceled", "cancelled", "expired"}:
        return OrderStatus.CANCELLED
    return OrderStatus.FAILED


def _apply_fill_to_portfolio(
    *,
    broker_result: BrokerOrderResult,
    portfolio: PortfolioModel,
    experiment_id: int,
    execution_step_id: int,
    timestamp: datetime,
    now: datetime,
) -> TradeModel:
    fill_value = (
        broker_result.filled_quantity * broker_result.average_fill_price
    ).quantize(Decimal("0.0001"))
    if broker_result.side is OrderSide.BUY:
        portfolio.cash = (portfolio.cash - fill_value).quantize(Decimal("0.0001"))
        portfolio.position_symbol = broker_result.symbol
        portfolio.position_quantity = (
            (portfolio.position_quantity or Decimal("0")) + broker_result.filled_quantity
        )
    else:
        portfolio.cash = (portfolio.cash + fill_value).quantize(Decimal("0.0001"))
        remaining_quantity = (portfolio.position_quantity or Decimal("0")) - (
            broker_result.filled_quantity
        )
        if remaining_quantity <= 0:
            portfolio.position_symbol = None
            portfolio.position_quantity = Decimal("0")
            portfolio.current_position_value = Decimal("0.0000")
        else:
            portfolio.position_symbol = broker_result.symbol
            portfolio.position_quantity = remaining_quantity

    return TradeModel(
        execution_step_id=execution_step_id,
        experiment_id=experiment_id,
        order_id=0,
        timestamp=timestamp,
        symbol=broker_result.symbol,
        side=broker_result.side,
        quantity=broker_result.filled_quantity,
        price=broker_result.average_fill_price,
        order_value=fill_value,
        fee=Decimal("0"),
        portfolio_value_after_trade=None,
        created_at=now,
    )
