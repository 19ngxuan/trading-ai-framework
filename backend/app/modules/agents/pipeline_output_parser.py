import json
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain.enums import TradeAction
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
            confidence=self._parse_confidence(payload.get("confidence")),
            rationale=self._parse_text(payload.get("rationale"), "rationale"),
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

    def parse_portfolio_decision(self, raw_output_text: str) -> ParsedAgentOutput:
        return self.parse_trading_decision(raw_output_text)

    def _load_object(self, raw_output_text: str) -> dict[str, Any]:
        try:
            payload = json.loads(raw_output_text)
        except json.JSONDecodeError as exc:
            raise AgentOutputParseError("Pipeline output must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise AgentOutputParseError("Pipeline output must be a JSON object.")
        return payload

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

    def _parse_text(self, value: Any, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise AgentOutputParseError(f"Pipeline field {field_name} is required.")
        return value.strip()
