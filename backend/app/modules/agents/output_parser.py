import json
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain.enums import TradeAction
from app.modules.agents.types import ParsedAgentOutput


class AgentOutputParseError(ValueError):
    pass


class AgentOutputParser:
    def parse(self, raw_output_text: str) -> ParsedAgentOutput:
        try:
            payload = json.loads(raw_output_text)
        except json.JSONDecodeError as exc:
            raise AgentOutputParseError("Agent output must be valid JSON.") from exc

        if not isinstance(payload, dict):
            raise AgentOutputParseError("Agent output must be a JSON object.")

        action = self._parse_action(payload.get("action"))
        confidence = self._parse_confidence(payload.get("confidence"))
        rationale = self._parse_rationale(payload.get("rationale"))
        return ParsedAgentOutput(
            action=action,
            confidence=confidence,
            rationale=rationale,
        )

    def _parse_action(self, value: Any) -> TradeAction:
        if not isinstance(value, str):
            raise AgentOutputParseError("Agent action is required.")
        try:
            return TradeAction(value.upper())
        except ValueError as exc:
            raise AgentOutputParseError(
                "Agent action must be BUY, SELL, or HOLD."
            ) from exc

    def _parse_confidence(self, value: Any) -> Decimal:
        try:
            confidence = Decimal(str(value))
        except (InvalidOperation, TypeError) as exc:
            raise AgentOutputParseError("Agent confidence is required.") from exc
        if confidence < 0 or confidence > 1:
            raise AgentOutputParseError("Agent confidence must be between 0 and 1.")
        return confidence.quantize(Decimal("0.0001"))

    def _parse_rationale(self, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise AgentOutputParseError("Agent rationale is required.")
        return value.strip()
