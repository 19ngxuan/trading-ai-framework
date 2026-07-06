from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from typing import Protocol

from app.domain.enums import FinalAction, TradeAction
from app.persistence.models import PortfolioModel


class StrategyDecisionLike(Protocol):
    action: TradeAction
    symbol: str
    reason: str


class TargetExposureDecisionLike(StrategyDecisionLike, Protocol):
    target_exposure_pct: Decimal | None


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

    def evaluate_target_exposure(
        self,
        decision: TargetExposureDecisionLike,
        portfolio: PortfolioModel,
        price: Decimal,
        *,
        max_exposure_pct: Decimal = Decimal("1.0000"),
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
        target_exposure_pct = decision.target_exposure_pct
        if target_exposure_pct is None:
            return self.evaluate(decision, portfolio, price)

        position_quantity = portfolio.position_quantity or Decimal("0")
        cash = portfolio.cash or Decimal("0")
        current_position_value = position_quantity * price
        portfolio_value = portfolio.current_portfolio_value
        if portfolio_value is None or portfolio_value <= 0:
            portfolio_value = cash + current_position_value
        if portfolio_value <= 0:
            return RiskResult(
                approved=True,
                final_action=FinalAction.HOLD,
                final_quantity=None,
                final_notional=None,
                rejection_reason="Portfolio value must be positive.",
                rules_triggered_json={"reason": "INVALID_PORTFOLIO_VALUE"},
            )

        clamped_target = min(max(target_exposure_pct, Decimal("0")), max_exposure_pct)
        target_position_value = portfolio_value * clamped_target
        delta_value = target_position_value - current_position_value
        audit = {
            "reason": "TARGET_EXPOSURE_RISK_CHECK",
            "targetExposure": {
                "targetExposurePct": float(clamped_target),
                "requestedTargetExposurePct": float(target_exposure_pct),
                "maxExposurePct": float(max_exposure_pct),
                "currentPositionValue": float(current_position_value),
                "targetPositionValue": float(target_position_value),
                "deltaValue": float(delta_value),
            },
        }

        if decision.action is TradeAction.HOLD or abs(delta_value) < price:
            audit["reason"] = "TARGET_EXPOSURE_BELOW_ONE_SHARE"
            return RiskResult(
                approved=True,
                final_action=FinalAction.HOLD,
                final_quantity=None,
                final_notional=None,
                rejection_reason=None,
                rules_triggered_json=audit,
            )

        if delta_value > 0:
            target_quantity = self._floor_whole_shares(delta_value / price)
            affordable_quantity = self._floor_whole_shares(cash / price)
            quantity = min(target_quantity, affordable_quantity)
            if quantity < 1:
                audit["reason"] = "INSUFFICIENT_CASH_FOR_TARGET_EXPOSURE"
                return RiskResult(
                    approved=True,
                    final_action=FinalAction.HOLD,
                    final_quantity=None,
                    final_notional=None,
                    rejection_reason="Insufficient cash for at least one share.",
                    rules_triggered_json=audit,
                )
            audit["targetExposure"]["finalQuantity"] = float(quantity)
            return RiskResult(
                approved=True,
                final_action=FinalAction.BUY,
                final_quantity=quantity,
                final_notional=(quantity * price).quantize(Decimal("0.0001")),
                rejection_reason=None,
                rules_triggered_json=audit,
            )

        if position_quantity <= 0:
            audit["reason"] = "NO_POSITION_TO_SELL"
            return RiskResult(
                approved=True,
                final_action=FinalAction.HOLD,
                final_quantity=None,
                final_notional=None,
                rejection_reason=f"No {decision.symbol} position exists to sell.",
                rules_triggered_json=audit,
            )
        quantity = min(
            self._floor_whole_shares(abs(delta_value) / price),
            position_quantity,
        )
        if quantity < 1:
            audit["reason"] = "TARGET_EXPOSURE_BELOW_ONE_SHARE"
            return RiskResult(
                approved=True,
                final_action=FinalAction.HOLD,
                final_quantity=None,
                final_notional=None,
                rejection_reason=None,
                rules_triggered_json=audit,
            )
        audit["targetExposure"]["finalQuantity"] = float(quantity)
        return RiskResult(
            approved=True,
            final_action=FinalAction.SELL,
            final_quantity=quantity,
            final_notional=(quantity * price).quantize(Decimal("0.0001")),
            rejection_reason=None,
            rules_triggered_json=audit,
        )


class BuyAndHoldRiskValidator(HistoricalSimulationRiskValidator):
    pass
