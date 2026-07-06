from decimal import Decimal
from typing import Any

from app.modules.agents.types import AgentContext


PROMPT_VERSION = "single-agent-v2-target-exposure"


class PromptBuilder:
    prompt_version = PROMPT_VERSION

    def build_input(self, context: AgentContext) -> dict[str, Any]:
        position_value = None
        current_exposure_pct = None
        if context.position_quantity is not None:
            position_value = context.position_quantity * context.bar.adjusted_close
        if (
            position_value is not None
            and context.current_portfolio_value is not None
            and context.current_portfolio_value > 0
        ):
            current_exposure_pct = position_value / context.current_portfolio_value
        return {
            "experimentId": context.experiment_id,
            "executionStepId": context.execution_step_id,
            "symbol": context.symbol,
            "bar": {
                "date": context.bar.date.isoformat(),
                "timestamp": context.bar.timestamp.isoformat()
                if context.bar.timestamp is not None
                else None,
                "open": self._decimal_to_string(context.bar.open),
                "high": self._decimal_to_string(context.bar.high),
                "low": self._decimal_to_string(context.bar.low),
                "close": self._decimal_to_string(context.bar.adjusted_close),
                "adjustedClose": self._decimal_to_string(context.bar.adjusted_close),
                "volume": self._decimal_to_string(context.bar.volume),
            },
            "portfolio": {
                "cash": self._decimal_to_string(context.cash),
                "positionQuantity": self._decimal_to_string(
                    context.position_quantity
                ),
                "positionMarketValue": self._decimal_to_string(position_value),
                "currentExposurePct": self._decimal_to_string(current_exposure_pct),
                "currentPortfolioValue": self._decimal_to_string(
                    context.current_portfolio_value
                ),
            },
            "confidenceThreshold": self._decimal_to_string(
                context.confidence_threshold
            ),
            "agentMode": context.agent_mode.value,
            "modelName": context.model_name,
            "eventContext": context.event_context,
        }

    def build_prompt(self, input_json: dict[str, Any]) -> str:
        return (
            "You are a single-agent trading strategy for a controlled trading "
            "workflow. You may only propose one advisory trading decision. You must not "
            "call broker, order, trade, portfolio, scheduler, persistence, tool, or "
            "Alpaca APIs. RiskCheck is mandatory and authoritative after your output. "
            "Return strict JSON only with fields: action BUY, SELL, or HOLD; "
            "tradeIntent OPEN_LONG, ADD_TO_LONG, HOLD_POSITION, REDUCE_LONG, "
            "CLOSE_LONG, or STAY_OUT; targetExposurePct between 0 and 1; "
            "confidence between 0 and 1; primaryDriver TECHNICAL, FUNDAMENTAL, "
            "SENTIMENT, RISK, PORTFOLIO, or EVENT_RISK; newInformation boolean; "
            "rationale; optional eventId. BUY means increase exposure, SELL means "
            "reduce exposure. Never propose all-in exposure without high conviction "
            "and low risk. Choose HOLD on uncertainty. Input: "
            f"{input_json}"
        )

    def build_repair_prompt(self, raw_output_text: str, error_message: str) -> str:
        return (
            "Repair the previous output into strict JSON with fields action, "
            "tradeIntent, targetExposurePct, confidence, primaryDriver, "
            "newInformation, rationale, and optional eventId only. Valid actions "
            "are BUY, SELL, HOLD. targetExposurePct must be between 0 and 1. "
            f"Parse error: {error_message}. Previous output: {raw_output_text}"
        )

    def _decimal_to_string(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return str(value)
