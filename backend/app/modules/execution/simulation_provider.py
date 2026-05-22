from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.enums import (
    BrokerName,
    FinalAction,
    OrderMode,
    OrderSide,
    OrderStatus,
    OrderType,
)
from app.modules.execution.risk import RiskResult
from app.persistence.models import OrderModel, PortfolioModel, TradeModel


@dataclass(frozen=True)
class SimulationResult:
    order: OrderModel | None
    trade: TradeModel | None


class SimulationExecutionProvider:
    def execute_buy_if_applicable(
        self,
        *,
        risk_result: RiskResult,
        portfolio: PortfolioModel,
        experiment_id: int,
        execution_step_id: int,
        risk_check_id: int,
        timestamp: datetime,
        price: Decimal,
        now: datetime,
    ) -> SimulationResult:
        return self.execute_if_applicable(
            risk_result=risk_result,
            portfolio=portfolio,
            experiment_id=experiment_id,
            execution_step_id=execution_step_id,
            risk_check_id=risk_check_id,
            timestamp=timestamp,
            price=price,
            now=now,
        )

    def execute_if_applicable(
        self,
        *,
        risk_result: RiskResult,
        portfolio: PortfolioModel,
        experiment_id: int,
        execution_step_id: int,
        risk_check_id: int,
        timestamp: datetime,
        price: Decimal,
        now: datetime,
    ) -> SimulationResult:
        if risk_result.final_action is FinalAction.HOLD:
            return SimulationResult(order=None, trade=None)

        quantity = risk_result.final_quantity
        if quantity is None:
            return SimulationResult(order=None, trade=None)

        order_value = (quantity * price).quantize(Decimal("0.0001"))
        if risk_result.final_action is FinalAction.BUY:
            side = OrderSide.BUY
            portfolio.cash = (portfolio.cash - order_value).quantize(Decimal("0.0001"))
            portfolio.position_symbol = "SPY"
            portfolio.position_quantity = (
                (portfolio.position_quantity or Decimal("0")) + quantity
            )
        elif risk_result.final_action is FinalAction.SELL:
            side = OrderSide.SELL
            portfolio.cash = (portfolio.cash + order_value).quantize(Decimal("0.0001"))
            portfolio.position_symbol = None
            portfolio.position_quantity = Decimal("0")
            portfolio.current_position_value = Decimal("0.0000")
        else:
            return SimulationResult(order=None, trade=None)

        order = OrderModel(
            execution_step_id=execution_step_id,
            experiment_id=experiment_id,
            risk_check_id=risk_check_id,
            mode=OrderMode.SIMULATED,
            broker_name=BrokerName.NONE,
            broker_order_id=None,
            symbol="SPY",
            side=side,
            quantity=quantity,
            order_type=OrderType.MARKET,
            status=OrderStatus.FILLED,
            submitted_at=timestamp,
            filled_at=timestamp,
            average_fill_price=price,
            error_message=None,
            created_at=now,
        )
        trade = TradeModel(
            execution_step_id=execution_step_id,
            experiment_id=experiment_id,
            order_id=0,
            timestamp=timestamp,
            symbol="SPY",
            side=side,
            quantity=quantity,
            price=price,
            order_value=order_value,
            fee=Decimal("0"),
            portfolio_value_after_trade=None,
            created_at=now,
        )
        return SimulationResult(order=order, trade=trade)
