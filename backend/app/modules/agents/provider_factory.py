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


class YahooResearchProvider:
    provider_name = "yahoo"

    def __init__(
        self,
        *,
        base_url: str = "https://query1.finance.yahoo.com",
        timeout_seconds: int = 10,
        news_lookback_hours: int = 24,
        news_limit: int = 20,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.news_lookback_hours = news_lookback_hours
        self.news_limit = news_limit
        self.client = client or httpx.Client(timeout=timeout_seconds)

    def load(self, context: AgentContext) -> FundamentalResearchSnapshot:
        return self.load_fundamental(context)

    def load_fundamental(self, context: AgentContext) -> FundamentalResearchSnapshot:
        symbol = context.symbol.upper()
        try:
            payload = self._quote_summary(
                symbol,
                (
                    "summaryProfile",
                    "summaryDetail",
                    "defaultKeyStatistics",
                    "financialData",
                    "recommendationTrend",
                    "earningsTrend",
                ),
            )
        except httpx.HTTPError:
            return FundamentalResearchSnapshot(source=self.provider_name)

        profile = _dict_or_empty(payload.get("summaryProfile"))
        summary_detail = _dict_or_empty(payload.get("summaryDetail"))
        key_stats = _dict_or_empty(payload.get("defaultKeyStatistics"))
        financial_data = _dict_or_empty(payload.get("financialData"))
        recommendation_trend = _dict_or_empty(payload.get("recommendationTrend"))
        earnings_trend = _dict_or_empty(payload.get("earningsTrend"))
        raw_data = _compact_payload(
            {
                "profile": profile,
                "summaryDetail": summary_detail,
                "defaultKeyStatistics": key_stats,
                "financialData": financial_data,
                "analystEstimates": earnings_trend,
                "analystRatings": recommendation_trend,
            }
        )
        return FundamentalResearchSnapshot(
            pe_ratio=_decimal_or_none(
                _yahoo_value(summary_detail.get("trailingPE"))
                or _yahoo_value(key_stats.get("trailingPE"))
            ),
            forward_pe=_decimal_or_none(
                _yahoo_value(summary_detail.get("forwardPE"))
                or _yahoo_value(key_stats.get("forwardPE"))
            ),
            market_cap=_decimal_or_none(_yahoo_value(summary_detail.get("marketCap"))),
            dividend_yield=_decimal_or_none(_yahoo_value(summary_detail.get("yield"))),
            profit_margins=_decimal_or_none(
                _yahoo_value(financial_data.get("profitMargins"))
            ),
            revenue_growth=_decimal_or_none(
                _yahoo_value(financial_data.get("revenueGrowth"))
            ),
            notes=_string_or_none(profile.get("longBusinessSummary")),
            raw_data=raw_data or None,
            analyst_estimates=earnings_trend or None,
            analyst_ratings=recommendation_trend or None,
            source=self.provider_name,
            data_available=bool(raw_data),
        )

    def load_sentiment(self, context: AgentContext) -> SentimentResearchSnapshot:
        symbol = context.symbol.upper()
        try:
            search_payload = self._get_object(
                "/v1/finance/search",
                {"q": symbol, "quotesCount": 0, "newsCount": self.news_limit},
            )
            analyst_payload = self._quote_summary(
                symbol,
                ("recommendationTrend",),
            )
        except httpx.HTTPError:
            return SentimentResearchSnapshot(source=self.provider_name)

        news = _dict_items(search_payload.get("news"))
        news_items, duplicate_count = _dedupe_news(news, self.news_limit)
        headlines = tuple(
            item["headline"] for item in news_items if isinstance(item.get("headline"), str)
        )
        source_weights = _source_weights(news_items)
        recommendation_trend = _dict_or_empty(analyst_payload.get("recommendationTrend"))
        raw_data = _compact_payload(
            {
                "newsItems": list(news_items),
                "analystComments": recommendation_trend,
                "duplicateCount": duplicate_count,
                "sourceWeights": source_weights,
            }
        )
        return SentimentResearchSnapshot(
            summary=_sentiment_summary(len(news_items), 0),
            headlines=headlines,
            raw_data=raw_data or None,
            news_items=news_items,
            analyst_comments=tuple(_dict_items(recommendation_trend.get("trend"))),
            transcript_summaries=(),
            source_weights=source_weights,
            time_weighting={
                "lookbackHours": self.news_lookback_hours,
                "newerItemsReceiveHigherWeight": True,
            },
            duplicate_count=duplicate_count,
            source=self.provider_name,
            news_available=bool(news_items),
            transcript_available=False,
        )

    def _quote_summary(self, symbol: str, modules: tuple[str, ...]) -> dict[str, Any]:
        payload = self._get_object(
            f"/v10/finance/quoteSummary/{symbol}",
            {"modules": ",".join(modules)},
        )
        result = _dict_or_empty(payload.get("quoteSummary")).get("result")
        if isinstance(result, list) and result and isinstance(result[0], dict):
            return result[0]
        return {}

    def _get_object(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        response = self.client.get(
            f"{self.base_url}{path}",
            params=params,
            headers={"User-Agent": "trading-ai-framework/0.1"},
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            return payload
        return {}


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
    if settings.research_data_provider == "yahoo":
        provider = YahooResearchProvider(
            base_url=settings.yahoo_base_url,
            timeout_seconds=settings.yahoo_request_timeout_seconds,
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
        key = _string_or_none(item.get("url") or item.get("link")) or headline.lower()
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        items.append(
            {
                "headline": headline,
                "publishedAt": item.get("providerPublishTime"),
                "source": item.get("publisher") or "Yahoo Finance",
                "url": item.get("link"),
                "snippet": _truncate(_string_or_none(item.get("summary")), 500),
            }
        )
        if len(items) >= limit:
            break
    return tuple(items), duplicate_count


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


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dict_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _yahoo_value(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("raw") if "raw" in value else value.get("fmt")
    return value
