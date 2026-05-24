from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.domain.enums import FinalAction, TradeAction
from app.modules.execution.position_sizing import calculate_position_size
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
    def _position_sizing_audit(
        *,
        sizing_type: str | None,
        sizing_value: Decimal | None,
        requested_quantity: Decimal | None,
        final_quantity: Decimal | None,
        sizing_reason: str,
    ) -> dict:
        return {
            "positionSizing": {
                "positionSizingType": sizing_type or "ALL_IN",
                "positionSizingValue": float(sizing_value)
                if sizing_value is not None
                else None,
                "requestedQuantity": float(requested_quantity)
                if requested_quantity is not None
                else None,
                "finalQuantity": float(final_quantity)
                if final_quantity is not None
                else None,
                "sizingReason": sizing_reason,
            }
        }

    def evaluate(
        self,
        decision: StrategyDecisionLike,
        portfolio: PortfolioModel,
        price: Decimal,
        position_sizing_type: str | None = None,
        position_sizing_value: Decimal | None = None,
    ) -> RiskResult:
        sizing_result = calculate_position_size(
            action=decision.action,
            cash=portfolio.cash,
            current_portfolio_value=portfolio.current_portfolio_value,
            current_position_quantity=portfolio.position_quantity,
            price=price,
            sizing_type=position_sizing_type,
            sizing_value=position_sizing_value,
        )
        audit_json = self._position_sizing_audit(
            sizing_type=position_sizing_type,
            sizing_value=position_sizing_value,
            requested_quantity=sizing_result.requested_quantity,
            final_quantity=sizing_result.final_quantity,
            sizing_reason=sizing_result.sizing_reason,
        )

        if decision.action is TradeAction.HOLD:
            return RiskResult(
                approved=True,
                final_action=FinalAction.HOLD,
                final_quantity=None,
                final_notional=None,
                rejection_reason=None,
                rules_triggered_json=audit_json,
            )

        if decision.action is TradeAction.SELL:
            if sizing_result.final_action is FinalAction.HOLD:
                audit_json["reason"] = "NO_POSITION_TO_SELL"
                return RiskResult(
                    approved=True,
                    final_action=FinalAction.HOLD,
                    final_quantity=None,
                    final_notional=None,
                    rejection_reason="No SPY position exists to sell.",
                    rules_triggered_json=audit_json,
                )

            quantity = sizing_result.final_quantity
            assert quantity is not None
            return RiskResult(
                approved=True,
                final_action=FinalAction.SELL,
                final_quantity=quantity,
                final_notional=(quantity * price).quantize(Decimal("0.0001")),
                rejection_reason=None,
                rules_triggered_json=audit_json,
            )

        if sizing_result.final_action is FinalAction.HOLD:
            audit_json["reason"] = "POSITION_SIZE_BELOW_ONE_SHARE"
            return RiskResult(
                approved=True,
                final_action=FinalAction.HOLD,
                final_quantity=None,
                final_notional=None,
                rejection_reason="Insufficient cash to buy at least one whole SPY share.",
                rules_triggered_json=audit_json,
            )

        quantity = sizing_result.final_quantity
        assert quantity is not None
        return RiskResult(
            approved=True,
            final_action=FinalAction.BUY,
            final_quantity=quantity,
            final_notional=(quantity * price).quantize(Decimal("0.0001")),
            rejection_reason=None,
            rules_triggered_json=audit_json,
        )


class BuyAndHoldRiskValidator(HistoricalSimulationRiskValidator):
    pass
