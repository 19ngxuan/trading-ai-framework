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
    def evaluate(
        self,
        decision: StrategyDecisionLike,
        portfolio: PortfolioModel,
        price: Decimal,
    ) -> RiskResult:
        if decision.action is TradeAction.HOLD:
            return RiskResult(
                approved=True,
                final_action=FinalAction.HOLD,
                final_quantity=None,
                final_notional=None,
                rejection_reason=None,
                rules_triggered_json=None,
            )

        if decision.action is TradeAction.SELL:
            quantity = portfolio.position_quantity or Decimal("0")
            if quantity <= 0:
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
                final_quantity=quantity,
                final_notional=(quantity * price).quantize(Decimal("0.0001")),
                rejection_reason=None,
                rules_triggered_json=None,
            )

        quantity = (portfolio.cash / price).to_integral_value(rounding=ROUND_FLOOR)
        if quantity < 1:
            return RiskResult(
                approved=True,
                final_action=FinalAction.HOLD,
                final_quantity=None,
                final_notional=None,
                rejection_reason="Insufficient cash to buy at least one whole SPY share.",
                rules_triggered_json={"reason": "INSUFFICIENT_CASH_FOR_WHOLE_SHARE"},
            )

        return RiskResult(
            approved=True,
            final_action=FinalAction.BUY,
            final_quantity=quantity,
            final_notional=(quantity * price).quantize(Decimal("0.0001")),
            rejection_reason=None,
            rules_triggered_json=None,
        )


class BuyAndHoldRiskValidator(HistoricalSimulationRiskValidator):
    pass
