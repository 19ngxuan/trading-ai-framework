from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR

from app.domain.enums import FinalAction, TradeAction
from app.modules.strategies.buy_and_hold import StrategyDecision
from app.persistence.models import PortfolioModel


@dataclass(frozen=True)
class RiskResult:
    approved: bool
    final_action: FinalAction
    final_quantity: Decimal | None
    final_notional: Decimal | None
    rejection_reason: str | None
    rules_triggered_json: dict | None


class BuyAndHoldRiskValidator:
    def evaluate(
        self,
        decision: StrategyDecision,
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
