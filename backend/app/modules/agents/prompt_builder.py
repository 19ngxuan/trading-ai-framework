from decimal import Decimal
from typing import Any

from app.modules.agents.types import AgentContext


PROMPT_VERSION = "single-agent-v1"


class PromptBuilder:
    prompt_version = PROMPT_VERSION

    def build_input(self, context: AgentContext) -> dict[str, Any]:
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
                "currentPortfolioValue": self._decimal_to_string(
                    context.current_portfolio_value
                ),
            },
            "confidenceThreshold": self._decimal_to_string(
                context.confidence_threshold
            ),
            "agentMode": context.agent_mode.value,
            "modelName": context.model_name,
        }

    def build_prompt(self, input_json: dict[str, Any]) -> str:
        return (
            "You are a single-agent trading strategy for a controlled trading "
            "workflow. You may only propose one advisory SPY action. You must not "
            "call broker, order, trade, portfolio, scheduler, persistence, tool, or "
            "Alpaca APIs. RiskCheck is mandatory and authoritative after your output. "
            "Return strict JSON only with action BUY, SELL, or HOLD, confidence "
            "between 0 and 1, and rationale. Input: "
            f"{input_json}"
        )

    def build_repair_prompt(self, raw_output_text: str, error_message: str) -> str:
        return (
            "Repair the previous output into strict JSON with fields action, "
            "confidence, and rationale only. Valid actions are BUY, SELL, HOLD. "
            f"Parse error: {error_message}. Previous output: {raw_output_text}"
        )

    def _decimal_to_string(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return str(value)
