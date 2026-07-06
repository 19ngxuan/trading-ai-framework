from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import TradeAction, TradeIntent
from app.modules.agents.types import AgentContext, ParsedAgentOutput


@dataclass(frozen=True)
class DecisionGateResult:
    decision: ParsedAgentOutput
    audit_json: dict


class AgentDecisionGate:
    def apply(
        self,
        parsed: ParsedAgentOutput,
        context: AgentContext,
        *,
        risk_level: str | None = None,
        max_exposure_pct: Decimal = Decimal("1.0000"),
    ) -> DecisionGateResult:
        current_exposure_pct = self._current_exposure_pct(context)
        target_exposure_pct = min(parsed.target_exposure_pct, max_exposure_pct)
        clamped = target_exposure_pct != parsed.target_exposure_pct
        fallback_reason: str | None = None
        threshold_applied = False

        final_action = parsed.action
        final_intent = parsed.trade_intent
        final_rationale = parsed.rationale

        if context.confidence_threshold is not None and parsed.confidence < context.confidence_threshold:
            final_action = TradeAction.HOLD
            final_intent = self._hold_intent(context)
            threshold_applied = True
            fallback_reason = "CONFIDENCE_BELOW_THRESHOLD"
            final_rationale = (
                f"Agent confidence {parsed.confidence} is below configured threshold "
                f"{context.confidence_threshold}; converted to HOLD before RiskCheck."
            )
        elif parsed.action is TradeAction.BUY and target_exposure_pct <= current_exposure_pct:
            final_action = TradeAction.HOLD
            final_intent = self._hold_intent(context)
            fallback_reason = "BUY_TARGET_NOT_ABOVE_CURRENT_EXPOSURE"
            final_rationale = (
                "BUY was converted to HOLD because target exposure is not above "
                "current exposure."
            )
        elif parsed.action is TradeAction.SELL and not self._has_position(context):
            final_action = TradeAction.HOLD
            final_intent = TradeIntent.STAY_OUT
            fallback_reason = "SELL_WITHOUT_POSITION"
            final_rationale = "SELL was converted to HOLD because no long position exists."
        elif parsed.action is TradeAction.SELL and target_exposure_pct >= current_exposure_pct:
            final_action = TradeAction.HOLD
            final_intent = self._hold_intent(context)
            fallback_reason = "SELL_TARGET_NOT_BELOW_CURRENT_EXPOSURE"
            final_rationale = (
                "SELL was converted to HOLD because target exposure is not below "
                "current exposure."
            )
        elif parsed.action is TradeAction.BUY and not parsed.new_information:
            final_action = TradeAction.HOLD
            final_intent = self._hold_intent(context)
            fallback_reason = "BUY_WITHOUT_NEW_INFORMATION"
            final_rationale = (
                "BUY was converted to HOLD because the agent did not identify new "
                "information."
            )
        elif parsed.action is TradeAction.BUY and risk_level == "HIGH":
            final_action = TradeAction.HOLD
            final_intent = self._hold_intent(context)
            fallback_reason = "AGENT_RISK_MANAGER_BLOCKED_BUY"
            final_rationale = (
                "BUY was converted to HOLD because the agent risk stage reported HIGH risk."
            )

        final_decision = ParsedAgentOutput(
            action=final_action,
            trade_intent=final_intent,
            target_exposure_pct=target_exposure_pct
            if final_action is not TradeAction.HOLD
            else current_exposure_pct,
            confidence=parsed.confidence,
            primary_driver=parsed.primary_driver,
            new_information=parsed.new_information,
            rationale=final_rationale,
            event_id=parsed.event_id,
        )
        return DecisionGateResult(
            decision=final_decision,
            audit_json={
                "originalAction": parsed.action.value,
                "originalTradeIntent": parsed.trade_intent.value,
                "originalTargetExposurePct": float(parsed.target_exposure_pct),
                "originalConfidence": float(parsed.confidence),
                "currentExposurePct": float(current_exposure_pct),
                "finalAction": final_decision.action.value,
                "finalTradeIntent": final_decision.trade_intent.value,
                "finalTargetExposurePct": float(final_decision.target_exposure_pct),
                "primaryDriver": final_decision.primary_driver.value,
                "newInformation": final_decision.new_information,
                "fallbackUsed": fallback_reason is not None,
                "fallbackReason": fallback_reason,
                "confidenceThresholdApplied": threshold_applied,
                "targetExposureClamped": clamped,
                "maxExposurePct": float(max_exposure_pct),
                "riskLevel": risk_level,
            },
        )

    def _current_exposure_pct(self, context: AgentContext) -> Decimal:
        portfolio_value = context.current_portfolio_value
        if portfolio_value is None or portfolio_value <= 0:
            portfolio_value = context.cash + self._position_value(context)
        if portfolio_value <= 0:
            return Decimal("0.0000")
        return (self._position_value(context) / portfolio_value).quantize(
            Decimal("0.0001")
        )

    def _position_value(self, context: AgentContext) -> Decimal:
        quantity = context.position_quantity or Decimal("0")
        return quantity * context.bar.adjusted_close

    def _has_position(self, context: AgentContext) -> bool:
        return (context.position_quantity or Decimal("0")) > 0

    def _hold_intent(self, context: AgentContext) -> TradeIntent:
        return TradeIntent.HOLD_POSITION if self._has_position(context) else TradeIntent.STAY_OUT
