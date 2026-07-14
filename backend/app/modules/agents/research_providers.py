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
    analyst_estimates: dict[str, Any] | None = None
    analyst_ratings: dict[str, Any] | None = None
    source: str = "parameters"
    data_available: bool = False


@dataclass(frozen=True)
class SentimentResearchSnapshot:
    summary: str | None = None
    headlines: tuple[str, ...] = ()
    signal: str | None = None
    confidence: Decimal | None = None
    raw_data: dict[str, Any] | None = None
    news_items: tuple[dict[str, Any], ...] = ()
    analyst_comments: tuple[dict[str, Any], ...] = ()
    transcript_summaries: tuple[dict[str, Any], ...] = ()
    source_weights: dict[str, float] | None = None
    time_weighting: dict[str, Any] | None = None
    duplicate_count: int = 0
    contradiction_notes: tuple[str, ...] = ()
    source: str = "parameters"
    news_available: bool = False
    transcript_available: bool = False


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
            analyst_estimates=_dict_or_none(payload.get("analystEstimates")),
            analyst_ratings=_dict_or_none(payload.get("analystRatings")),
            data_available=bool(payload),
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
            news_items=tuple(_dict_items(payload.get("newsItems"))),
            analyst_comments=tuple(_dict_items(payload.get("analystComments"))),
            transcript_summaries=tuple(_dict_items(payload.get("transcriptSummaries"))),
            source_weights=_dict_or_none(payload.get("sourceWeights")),
            time_weighting=_dict_or_none(payload.get("timeWeighting")),
            duplicate_count=int(payload.get("duplicateCount") or 0),
            contradiction_notes=tuple(
                item.strip()
                for item in payload.get("contradictionNotes", [])
                if isinstance(item, str) and item.strip()
            ),
            news_available=bool(payload.get("headlines") or payload.get("newsItems")),
            transcript_available=bool(payload.get("transcriptSummaries")),
        )


class CompositeResearchProvider:
    def __init__(
        self,
        fundamental_provider: FundamentalResearchProvider,
        sentiment_provider: SentimentResearchProvider,
    ) -> None:
        self.fundamental_provider = fundamental_provider
        self.sentiment_provider = sentiment_provider

    def load_fundamental(self, context: AgentContext) -> FundamentalResearchSnapshot:
        provider = self.fundamental_provider
        if hasattr(provider, "load_fundamental"):
            return provider.load_fundamental(context)  # type: ignore[attr-defined]
        return provider.load(context)

    def load_sentiment(self, context: AgentContext) -> SentimentResearchSnapshot:
        provider = self.sentiment_provider
        if hasattr(provider, "load_sentiment"):
            return provider.load_sentiment(context)  # type: ignore[attr-defined]
        return provider.load(context)

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


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _dict_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []

