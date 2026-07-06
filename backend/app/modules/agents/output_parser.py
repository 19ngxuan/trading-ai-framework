import json
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain.enums import PrimaryDriver, TradeAction, TradeIntent
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
        trade_intent = self._parse_trade_intent(payload.get("tradeIntent"))
        target_exposure_pct = self._parse_target_exposure_pct(
            payload.get("targetExposurePct")
        )
        confidence = self._parse_confidence(payload.get("confidence"))
        primary_driver = self._parse_primary_driver(payload.get("primaryDriver"))
        new_information = self._parse_new_information(payload.get("newInformation"))
        rationale = self._parse_rationale(payload.get("rationale"))
        event_id = self._parse_optional_text(payload.get("eventId"), "eventId")
        return ParsedAgentOutput(
            action=action,
            trade_intent=trade_intent,
            target_exposure_pct=target_exposure_pct,
            confidence=confidence,
            primary_driver=primary_driver,
            new_information=new_information,
            rationale=rationale,
            event_id=event_id,
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

    def _parse_trade_intent(self, value: Any) -> TradeIntent:
        if not isinstance(value, str):
            raise AgentOutputParseError("Agent tradeIntent is required.")
        try:
            return TradeIntent(value.upper())
        except ValueError as exc:
            allowed = ", ".join(item.value for item in TradeIntent)
            raise AgentOutputParseError(
                f"Agent tradeIntent must be one of {allowed}."
            ) from exc

    def _parse_primary_driver(self, value: Any) -> PrimaryDriver:
        if not isinstance(value, str):
            raise AgentOutputParseError("Agent primaryDriver is required.")
        try:
            return PrimaryDriver(value.upper())
        except ValueError as exc:
            allowed = ", ".join(item.value for item in PrimaryDriver)
            raise AgentOutputParseError(
                f"Agent primaryDriver must be one of {allowed}."
            ) from exc

    def _parse_target_exposure_pct(self, value: Any) -> Decimal:
        try:
            target_exposure_pct = Decimal(str(value))
        except (InvalidOperation, TypeError) as exc:
            raise AgentOutputParseError(
                "Agent targetExposurePct is required."
            ) from exc
        if target_exposure_pct < 0 or target_exposure_pct > 1:
            raise AgentOutputParseError(
                "Agent targetExposurePct must be between 0 and 1."
            )
        return target_exposure_pct.quantize(Decimal("0.0001"))

    def _parse_confidence(self, value: Any) -> Decimal:
        try:
            confidence = Decimal(str(value))
        except (InvalidOperation, TypeError) as exc:
            raise AgentOutputParseError("Agent confidence is required.") from exc
        if confidence < 0 or confidence > 1:
            raise AgentOutputParseError("Agent confidence must be between 0 and 1.")
        return confidence.quantize(Decimal("0.0001"))

    def _parse_new_information(self, value: Any) -> bool:
        if not isinstance(value, bool):
            raise AgentOutputParseError("Agent newInformation is required.")
        return value

    def _parse_rationale(self, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise AgentOutputParseError("Agent rationale is required.")
        return value.strip()

    def _parse_optional_text(self, value: Any, field_name: str) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise AgentOutputParseError(f"Agent {field_name} must be a string.")
        return value.strip()
