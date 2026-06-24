from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

from app.modules.agents.types import AgentContext


@dataclass(frozen=True)
class FundamentalResearchSnapshot:
    pe_ratio: Decimal | None = None
    forward_pe: Decimal | None = None
    market_cap: Decimal | None = None
    dividend_yield: Decimal | None = None
    profit_margins: Decimal | None = None
    revenue_growth: Decimal | None = None
    notes: str | None = None
    raw_data: dict[str, Any] | None = None


@dataclass(frozen=True)
class SentimentResearchSnapshot:
    summary: str | None = None
    headlines: tuple[str, ...] = ()
    signal: str | None = None
    confidence: Decimal | None = None
    raw_data: dict[str, Any] | None = None


class FundamentalResearchProvider(Protocol):
    def load(self, context: AgentContext) -> FundamentalResearchSnapshot:
        ...


class SentimentResearchProvider(Protocol):
    def load(self, context: AgentContext) -> SentimentResearchSnapshot:
        ...


class ParameterFundamentalResearchProvider:
    def load(self, context: AgentContext) -> FundamentalResearchSnapshot:
        payload = _research_payload(context.parameters_json, "fundamentalData")
        return FundamentalResearchSnapshot(
            pe_ratio=_decimal_or_none(payload.get("peRatio")),
            forward_pe=_decimal_or_none(payload.get("forwardPe")),
            market_cap=_decimal_or_none(payload.get("marketCap")),
            dividend_yield=_decimal_or_none(payload.get("dividendYield")),
            profit_margins=_decimal_or_none(payload.get("profitMargins")),
            revenue_growth=_decimal_or_none(payload.get("revenueGrowth")),
            notes=_string_or_none(payload.get("notes")),
            raw_data=payload or None,
        )


class ParameterSentimentResearchProvider:
    def load(self, context: AgentContext) -> SentimentResearchSnapshot:
        payload = _research_payload(context.parameters_json, "sentimentData")
        confidence = _decimal_or_none(payload.get("confidence"))
        headlines = tuple(
            headline.strip()
            for headline in payload.get("headlines", [])
            if isinstance(headline, str) and headline.strip()
        )
        return SentimentResearchSnapshot(
            summary=_string_or_none(payload.get("summary")),
            headlines=headlines,
            signal=_string_or_none(payload.get("signal")),
            confidence=confidence.quantize(Decimal("0.0001"))
            if confidence is not None
            else None,
            raw_data=payload or None,
        )


def _research_payload(
    parameters_json: dict[str, Any] | None,
    key: str,
) -> dict[str, Any]:
    parameters = parameters_json or {}
    direct = parameters.get(key)
    if isinstance(direct, dict):
        return direct
    nested = parameters.get("researchContext")
    if isinstance(nested, dict):
        nested_value = nested.get(key)
        if isinstance(nested_value, dict):
            return nested_value
    multi_agent = parameters.get("multiAgent")
    if isinstance(multi_agent, dict):
        nested_value = multi_agent.get(key)
        if isinstance(nested_value, dict):
            return nested_value
    return {}


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


def _string_or_none(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
