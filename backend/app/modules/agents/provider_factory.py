from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.core.config import Settings
from app.modules.agents.errors import AgentProviderConfigurationError
from app.modules.agents.fake_provider import FakeAgentProvider
from app.modules.agents.research_providers import (
    CompositeResearchProvider,
    FundamentalResearchSnapshot,
    ParameterFundamentalResearchProvider,
    ParameterSentimentResearchProvider,
    SentimentResearchSnapshot,
)
from app.modules.agents.scads_provider import (
    ScadsAIAgentProvider,
    ScadsAIPipelineProvider,
)
from app.modules.agents.pipeline_types import PipelineProvider
from app.modules.agents.types import AgentContext, AgentProvider


class FmpResearchProvider:
    provider_name = "fmp"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://financialmodelingprep.com/stable",
        timeout_seconds: int = 10,
        news_lookback_hours: int = 24,
        news_limit: int = 20,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.news_lookback_hours = news_lookback_hours
        self.news_limit = news_limit
        self.client = client or httpx.Client(timeout=timeout_seconds)

    def load(self, context: AgentContext) -> FundamentalResearchSnapshot:
        return self.load_fundamental(context)

    def load_fundamental(self, context: AgentContext) -> FundamentalResearchSnapshot:
        symbol = context.symbol.upper()
        try:
            profile = _first(
                self._get_list("/profile", {"symbol": symbol})
            )
            ratios = _first(self._get_list("/ratios", {"symbol": symbol, "limit": 1}))
            income_statement = _first(
                self._get_list("/income-statement", {"symbol": symbol, "limit": 1})
            )
            estimates = self._get_list(
                "/analyst-estimates", {"symbol": symbol, "limit": 4}
            )
            ratings = self._get_list("/ratings-snapshot", {"symbol": symbol})
        except httpx.HTTPError:
            return FundamentalResearchSnapshot(source=self.provider_name)

        raw_data = _compact_payload(
            {
                "profile": profile,
                "ratios": ratios,
                "incomeStatement": income_statement,
                "analystEstimates": estimates[:4],
                "analystRatings": ratings[:3],
            }
        )
        return FundamentalResearchSnapshot(
            pe_ratio=_decimal_or_none(
                ratios.get("priceEarningsRatio")
                or ratios.get("peRatio")
                or profile.get("pe")
            ),
            forward_pe=_decimal_or_none(
                ratios.get("forwardPE")
                or ratios.get("forwardPe")
                or profile.get("forwardPE")
            ),
            market_cap=_decimal_or_none(profile.get("marketCap")),
            dividend_yield=_decimal_or_none(
                ratios.get("dividendYield") or profile.get("lastDiv")
            ),
            profit_margins=_decimal_or_none(
                ratios.get("netProfitMargin") or profile.get("profitMargins")
            ),
            revenue_growth=_decimal_or_none(ratios.get("revenueGrowth")),
            notes=_string_or_none(profile.get("description")),
            raw_data=raw_data or None,
            analyst_estimates={"items": estimates[:4]} if estimates else None,
            analyst_ratings={"items": ratings[:3]} if ratings else None,
            source=self.provider_name,
            data_available=bool(raw_data),
        )

    def load_sentiment(self, context: AgentContext) -> SentimentResearchSnapshot:
        symbol = context.symbol.upper()
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=self.news_lookback_hours)
        try:
            news = self._get_list(
                "/news/stock",
                {
                    "symbols": symbol,
                    "from": start.date().isoformat(),
                    "to": now.date().isoformat(),
                    "limit": self.news_limit,
                },
            )
            transcript_dates = self._safe_get_list(
                "/earning-call-transcript-dates", {"symbol": symbol}
            )
            transcripts = self._load_transcripts(symbol, transcript_dates[:2])
            ratings = self._safe_get_list("/ratings-snapshot", {"symbol": symbol})
        except httpx.HTTPError:
            return SentimentResearchSnapshot(source=self.provider_name)

        news_items, duplicate_count = _dedupe_news(news, self.news_limit)
        transcript_summaries = tuple(
            _transcript_summary(item) for item in transcripts[:2] if isinstance(item, dict)
        )
        headlines = tuple(
            item["headline"] for item in news_items if isinstance(item.get("headline"), str)
        )
        source_weights = _source_weights(news_items)
        raw_data = _compact_payload(
            {
                "newsItems": list(news_items),
                "transcriptSummaries": list(transcript_summaries),
                "analystComments": ratings[:3],
                "duplicateCount": duplicate_count,
                "sourceWeights": source_weights,
            }
        )
        return SentimentResearchSnapshot(
            summary=_sentiment_summary(len(news_items), len(transcript_summaries)),
            headlines=headlines,
            raw_data=raw_data or None,
            news_items=news_items,
            analyst_comments=tuple(ratings[:3]),
            transcript_summaries=transcript_summaries,
            source_weights=source_weights,
            time_weighting={
                "lookbackHours": self.news_lookback_hours,
                "newerItemsReceiveHigherWeight": True,
            },
            duplicate_count=duplicate_count,
            source=self.provider_name,
            news_available=bool(news_items),
            transcript_available=bool(transcript_summaries),
        )

    def _get_list(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        response = self.client.get(
            f"{self.base_url}{path}",
            params={**params, "apikey": self.api_key},
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            if isinstance(payload.get("data"), list):
                return [item for item in payload["data"] if isinstance(item, dict)]
            return [payload]
        return []

    def _safe_get_list(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            return self._get_list(path, params)
        except httpx.HTTPError:
            return []

    def _load_transcripts(
        self, symbol: str, transcript_dates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        transcripts: list[dict[str, Any]] = []
        for item in transcript_dates:
            year = item.get("year")
            quarter = item.get("quarter")
            if year is None or quarter is None:
                continue
            transcripts.extend(
                self._safe_get_list(
                    "/earning-call-transcript",
                    {"symbol": symbol, "year": year, "quarter": quarter},
                )
            )
        return transcripts


def create_historical_agent_provider() -> AgentProvider:
    return FakeAgentProvider()


def create_scads_agent_provider(settings: Settings, model_name: str | None) -> AgentProvider:
    _validated_model(settings, model_name)
    return ScadsAIAgentProvider(
        api_key=settings.scadsai_api_key or "",
        base_url=settings.scadsai_base_url,
        timeout_seconds=settings.scadsai_request_timeout_seconds,
    )


def create_scads_pipeline_provider(
    settings: Settings, model_name: str | None
) -> PipelineProvider:
    _validated_model(settings, model_name)
    return ScadsAIPipelineProvider(
        api_key=settings.scadsai_api_key or "",
        base_url=settings.scadsai_base_url,
        timeout_seconds=settings.scadsai_request_timeout_seconds,
    )


def create_research_provider(settings: Settings) -> CompositeResearchProvider:
    if settings.research_data_provider == "fmp" and settings.fmp_api_key:
        provider = FmpResearchProvider(
            api_key=settings.fmp_api_key,
            base_url=settings.fmp_base_url,
            timeout_seconds=settings.fmp_request_timeout_seconds,
            news_lookback_hours=settings.multi_agent_news_lookback_hours,
            news_limit=settings.multi_agent_news_limit,
        )
        return CompositeResearchProvider(provider, provider)
    return CompositeResearchProvider(
        ParameterFundamentalResearchProvider(),
        ParameterSentimentResearchProvider(),
    )


def _validated_model(settings: Settings, model_name: str | None) -> str:
    if not settings.scadsai_llm_enabled:
        raise AgentProviderConfigurationError(
            "ScaDS.AI LLM provider is disabled.",
            details={"requiredConfig": "SCADSAI_LLM_ENABLED=true"},
        )
    if not settings.scadsai_api_key:
        raise AgentProviderConfigurationError(
            "ScaDS.AI API key is required.",
            details={"requiredConfig": "SCADSAI_API_KEY"},
        )
    selected_model = model_name or settings.scadsai_default_model
    allowed_models = settings.scadsai_allowed_model_list
    if selected_model not in allowed_models:
        raise AgentProviderConfigurationError(
            "Selected ScaDS.AI model is not allowed.",
            details={"modelName": selected_model, "allowedModels": allowed_models},
        )
    return selected_model


def _first(items: list[dict[str, Any]]) -> dict[str, Any]:
    return items[0] if items else {}


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


def _compact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value not in ({}, [], None)}


def _dedupe_news(
    news: list[dict[str, Any]], limit: int
) -> tuple[tuple[dict[str, Any], ...], int]:
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    duplicate_count = 0
    for item in news:
        headline = _string_or_none(item.get("title") or item.get("headline"))
        if headline is None:
            continue
        key = _string_or_none(item.get("url")) or headline.lower()
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        items.append(
            {
                "headline": headline,
                "publishedAt": item.get("publishedDate") or item.get("date"),
                "source": item.get("site") or item.get("publisher") or "FMP",
                "url": item.get("url"),
                "snippet": _truncate(_string_or_none(item.get("text")), 500),
            }
        )
        if len(items) >= limit:
            break
    return tuple(items), duplicate_count


def _transcript_summary(item: dict[str, Any]) -> dict[str, Any]:
    content = _string_or_none(item.get("content") or item.get("transcript"))
    return {
        "quarter": item.get("quarter"),
        "year": item.get("year"),
        "date": item.get("date"),
        "contentPreview": _truncate(content, 1000),
    }


def _source_weights(news_items: tuple[dict[str, Any], ...]) -> dict[str, float]:
    weights: dict[str, float] = {}
    if not news_items:
        return weights
    weight = 1 / len(news_items)
    for item in news_items:
        source = item.get("source")
        if isinstance(source, str) and source:
            weights[source] = round(weights.get(source, 0) + weight, 4)
    return weights


def _sentiment_summary(news_count: int, transcript_count: int) -> str | None:
    if news_count == 0 and transcript_count == 0:
        return None
    return (
        f"Loaded {news_count} asset-specific news item(s) and "
        f"{transcript_count} earnings-call transcript summary item(s)."
    )


def _truncate(value: str | None, max_length: int) -> str | None:
    if value is None or len(value) <= max_length:
        return value
    return f"{value[:max_length].rstrip()}..."
