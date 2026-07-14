import json
from json import JSONDecodeError
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain.enums import PrimaryDriver, TradeAction, TradeIntent
from app.modules.agents.output_parser import AgentOutputParseError
from app.modules.agents.pipeline_types import (
    FundamentalAnalysisOutput,
    MarketAnalysisOutput,
    MarketBias,
    RiskAssessmentOutput,
    RiskLevel,
    RiskManagerOutput,
    RiskManagerVerdict,
    SentimentAnalysisOutput,
    TechnicalAnalysisOutput,
)
from app.modules.agents.types import ParsedAgentOutput


class PipelineOutputParser:
    def parse_market_analysis(self, raw_output_text: str) -> MarketAnalysisOutput:
        payload = self._load_object(raw_output_text)
        bias = self._parse_enum(payload.get("marketBias"), MarketBias, "marketBias")
        return MarketAnalysisOutput(
            market_bias=bias,
            confidence=self._parse_confidence(payload.get("confidence")),
            rationale=self._parse_text(payload.get("rationale"), "rationale"),
        )

    def parse_trading_decision(self, raw_output_text: str) -> ParsedAgentOutput:
        payload = self._load_object(raw_output_text)
        action = self._parse_enum(payload.get("action"), TradeAction, "action")
        return ParsedAgentOutput(
            action=action,
            trade_intent=self._parse_enum(
                payload.get("tradeIntent"), TradeIntent, "tradeIntent"
            ),
            target_exposure_pct=self._parse_exposure(
                payload.get("targetExposurePct")
            ),
            confidence=self._parse_confidence(payload.get("confidence")),
            primary_driver=self._parse_enum(
                payload.get("primaryDriver"), PrimaryDriver, "primaryDriver"
            ),
            new_information=self._parse_bool(
                payload.get("newInformation"), "newInformation"
            ),
            rationale=self._parse_text(payload.get("rationale"), "rationale"),
            event_id=self._parse_optional_text(payload.get("eventId"), "eventId"),
        )

    def parse_risk_manager(self, raw_output_text: str) -> RiskManagerOutput:
        payload = self._load_object(raw_output_text)
        verdict = self._parse_enum(
            payload.get("verdict"), RiskManagerVerdict, "verdict"
        )
        return RiskManagerOutput(
            verdict=verdict,
            confidence=self._parse_confidence(payload.get("confidence")),
            rationale=self._parse_text(payload.get("rationale"), "rationale"),
        )

    def parse_fundamental_analysis(
        self, raw_output_text: str
    ) -> FundamentalAnalysisOutput:
        payload = self._load_object(raw_output_text)
        signal = self._parse_enum(payload.get("signal"), MarketBias, "signal")
        return FundamentalAnalysisOutput(
            signal=signal,
            confidence=self._parse_confidence(payload.get("confidence")),
            summary=self._parse_text(payload.get("summary"), "summary"),
        )

    def parse_sentiment_analysis(
        self, raw_output_text: str
    ) -> SentimentAnalysisOutput:
        payload = self._load_object(raw_output_text)
        signal = self._parse_enum(payload.get("signal"), MarketBias, "signal")
        return SentimentAnalysisOutput(
            signal=signal,
            confidence=self._parse_confidence(payload.get("confidence")),
            summary=self._parse_text(payload.get("summary"), "summary"),
        )

    def parse_risk_assessment(self, raw_output_text: str) -> RiskAssessmentOutput:
        payload = self._load_object(raw_output_text)
        risk_level = self._parse_enum(payload.get("riskLevel"), RiskLevel, "riskLevel")
        return RiskAssessmentOutput(
            risk_level=risk_level,
            confidence=self._parse_confidence(payload.get("confidence")),
            summary=self._parse_text(payload.get("summary"), "summary"),
        )

    def parse_technical_analysis(self, raw_output_text: str) -> TechnicalAnalysisOutput:
        payload = self._load_object(raw_output_text)
        signal = self._parse_enum(payload.get("signal"), MarketBias, "signal")
        summary = self._parse_text(
            payload.get("summary") or payload.get("rationale"), "summary"
        )
        return TechnicalAnalysisOutput(
            signal=signal,
            confidence=self._parse_confidence(payload.get("confidence")),
            rationale=summary,
            rsi=self._parse_optional_decimal(payload.get("rsi")),
            sma_20=self._parse_optional_decimal(payload.get("sma20")),
            trend=self._parse_optional_text(payload.get("trend"), "trend") or "UNKNOWN",
            volatility_pct=self._parse_optional_decimal(payload.get("volatilityPct")),
            indicators=self._parse_optional_object(payload.get("indicators")),
            time_horizon_signals=self._parse_optional_object(
                payload.get("timeHorizonSignals")
            ),
            risk_notes=self._parse_optional_string_list(payload.get("riskNotes")),
        )

    def parse_portfolio_decision(self, raw_output_text: str) -> ParsedAgentOutput:
        return self.parse_trading_decision(raw_output_text)

    def _load_object(self, raw_output_text: str) -> dict[str, Any]:
        try:
            payload = self._load_first_json_object(raw_output_text)
        except JSONDecodeError as exc:
            raise AgentOutputParseError("Pipeline output must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise AgentOutputParseError("Pipeline output must be a JSON object.")
        return payload

    def _load_first_json_object(self, raw_output_text: str) -> dict[str, Any]:
        text = raw_output_text.strip()
        try:
            return json.loads(text)
        except JSONDecodeError:
            pass

        decoder = json.JSONDecoder()
        for index, character in enumerate(text):
            if character != "{":
                continue
            try:
                payload, _ = decoder.raw_decode(text[index:])
            except JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload

        raise JSONDecodeError("Pipeline output must be valid JSON.", text, 0)

    def _parse_enum(self, value: Any, enum_type, field_name: str):
        if not isinstance(value, str):
            raise AgentOutputParseError(f"Pipeline field {field_name} is required.")
        try:
            return enum_type(value.upper())
        except ValueError as exc:
            allowed = ", ".join(item.value for item in enum_type)
            raise AgentOutputParseError(
                f"Pipeline field {field_name} must be one of {allowed}."
            ) from exc

    def _parse_confidence(self, value: Any) -> Decimal:
        try:
            confidence = Decimal(str(value))
        except (InvalidOperation, TypeError) as exc:
            raise AgentOutputParseError("Pipeline confidence is required.") from exc
        if confidence < 0 or confidence > 1:
            raise AgentOutputParseError("Pipeline confidence must be between 0 and 1.")
        return confidence.quantize(Decimal("0.0001"))

    def _parse_exposure(self, value: Any) -> Decimal:
        try:
            exposure = Decimal(str(value))
        except (InvalidOperation, TypeError) as exc:
            raise AgentOutputParseError(
                "Pipeline targetExposurePct is required."
            ) from exc
        if exposure < 0 or exposure > 1:
            raise AgentOutputParseError(
                "Pipeline targetExposurePct must be between 0 and 1."
            )
        return exposure.quantize(Decimal("0.0001"))

    def _parse_bool(self, value: Any, field_name: str) -> bool:
        if not isinstance(value, bool):
            raise AgentOutputParseError(f"Pipeline field {field_name} is required.")
        return value

    def _parse_text(self, value: Any, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise AgentOutputParseError(f"Pipeline field {field_name} is required.")
        return value.strip()

    def _parse_optional_text(self, value: Any, field_name: str) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise AgentOutputParseError(f"Pipeline field {field_name} must be text.")
        return value.strip()

    def _parse_optional_decimal(self, value: Any) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value)).quantize(Decimal("0.0001"))
        except (InvalidOperation, TypeError) as exc:
            raise AgentOutputParseError("Pipeline numeric field must be valid.") from exc

    def _parse_optional_object(self, value: Any) -> dict | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise AgentOutputParseError("Pipeline object field must be a JSON object.")
        return value

    def _parse_optional_string_list(self, value: Any) -> list[str] | None:
        if value is None:
            return None
        if not isinstance(value, list):
            raise AgentOutputParseError("Pipeline list field must be a JSON list.")
        return [str(item) for item in value]
