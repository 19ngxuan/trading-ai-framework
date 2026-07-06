from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from typing import Protocol

from app.domain.enums import FinalAction, TradeAction
from app.persistence.models import PortfolioModel


class StrategyDecisionLike(Protocol):
    action: TradeAction
    symbol: str
    reason: str


@dataclass(frozen=True)
class RiskResult:
    approved: bool
    final_action: FinalAction
    final_quantity: Decimal | None
    final_notional: Decimal | None
    rejection_reason: str | None
    rules_triggered_json: dict | None


class HistoricalSimulationRiskValidator:
    @staticmethod
    def _floor_whole_shares(value: Decimal) -> Decimal:
        return value.to_integral_value(rounding=ROUND_FLOOR)

    def evaluate(
        self,
        decision: StrategyDecisionLike,
        portfolio: PortfolioModel,
        price: Decimal,
    ) -> RiskResult:
        if price <= 0:
            return RiskResult(
                approved=True,
                final_action=FinalAction.HOLD,
                final_quantity=None,
                final_notional=None,
                rejection_reason="Execution price must be positive.",
                rules_triggered_json={"reason": "INVALID_EXECUTION_PRICE"},
            )

        if decision.action is TradeAction.HOLD:
            return RiskResult(
                approved=True,
                final_action=FinalAction.HOLD,
                final_quantity=None,
                final_notional=None,
                rejection_reason=None,
                rules_triggered_json={"reason": "HOLD_ACTION"},
            )

        if decision.action is TradeAction.SELL:
            position_quantity = portfolio.position_quantity or Decimal("0")
            if position_quantity <= 0:
                return RiskResult(
                    approved=True,
                    final_action=FinalAction.HOLD,
                    final_quantity=None,
                    final_notional=None,
                    rejection_reason=(
                        f"No {decision.symbol} position exists to sell."
                    ),
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

        quantity = self._floor_whole_shares(portfolio.cash / price)
        if quantity < 1:
            return RiskResult(
                approved=True,
                final_action=FinalAction.HOLD,
                final_quantity=None,
                final_notional=None,
                rejection_reason=(
                    "Insufficient cash to buy at least one whole "
                    f"{decision.symbol} share."
                ),
                rules_triggered_json={"reason": "INSUFFICIENT_CASH_FOR_ONE_SHARE"},
            )

        return RiskResult(
            approved=True,
            final_action=FinalAction.BUY,
            final_quantity=quantity,
            final_notional=(quantity * price).quantize(Decimal("0.0001")),
            rejection_reason=None,
            rules_triggered_json={"reason": "DEFAULT_WHOLE_SHARE_BUY"},
        )


class BuyAndHoldRiskValidator(HistoricalSimulationRiskValidator):
    pass
