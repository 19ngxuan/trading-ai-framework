from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

import httpx
from sqlalchemy.orm import Session

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
from app.persistence.repositories import ResearchDataCacheRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ResearchCache:
    def __init__(self, session: Session | None = None) -> None:
        self.repository = (
            ResearchDataCacheRepository(session) if session is not None else None
        )
        self.cache_hits = 0
        self.cache_misses = 0
        self.stale_fallback_used = False
        self.provider_breakdown: dict[str, Any] = {}

    def load(
        self,
        *,
        provider: str,
        symbol: str,
        dataset: str,
        cache_key: str,
        ttl: timedelta | None,
        fetch: Callable[[], dict[str, Any] | list[dict[str, Any]]],
    ) -> dict[str, Any] | list[dict[str, Any]]:
        now = _utcnow()
        repository = self.repository
        if repository is not None:
            cached = repository.get_fresh(
                provider=provider,
                symbol=symbol,
                dataset=dataset,
                cache_key=cache_key,
                now=now,
            )
            if cached is not None:
                self.cache_hits += 1
                self._record(provider, dataset, "hit")
                return cached.payload_json

        self.cache_misses += 1
        self._record(provider, dataset, "miss")
        try:
            payload = fetch()
        except httpx.HTTPError:
            if repository is None:
                raise
            stale = repository.get_latest_stale(
                provider=provider,
                symbol=symbol,
                dataset=dataset,
                cache_key=cache_key,
            )
            if stale is None:
                raise
            self.stale_fallback_used = True
            self.cache_hits += 1
            self._record(provider, dataset, "stale")
            return stale.payload_json

        if repository is not None:
            repository.upsert(
                provider=provider,
                symbol=symbol,
                dataset=dataset,
                cache_key=cache_key,
                payload_json=payload,
                fetched_at=now,
                expires_at=now + ttl if ttl is not None else None,
            )
        return payload

    def _record(self, provider: str, dataset: str, status: str) -> None:
        provider_data = self.provider_breakdown.setdefault(provider, {})
        dataset_data = provider_data.setdefault(
            dataset,
            {"cacheHits": 0, "cacheMisses": 0, "staleFallbacks": 0},
        )
        if status == "hit":
            dataset_data["cacheHits"] += 1
        elif status == "miss":
            dataset_data["cacheMisses"] += 1
        elif status == "stale":
            dataset_data["staleFallbacks"] += 1


class FmpFundamentalResearchProvider:
    provider_name = "fmp"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://financialmodelingprep.com/stable",
        timeout_seconds: int = 10,
        cache: ResearchCache | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=timeout_seconds)
        self.cache = cache or ResearchCache()

    def load(self, context: AgentContext) -> FundamentalResearchSnapshot:
        return self.load_fundamental(context)

    def load_fundamental(self, context: AgentContext) -> FundamentalResearchSnapshot:
        symbol = context.symbol.upper()
        try:
            profile = _first_list_item(
                self._cached_list(
                    symbol=symbol,
                    dataset="profile",
                    cache_key="latest",
                    ttl=timedelta(days=14),
                    fetch=lambda: self._get_list("/profile", {"symbol": symbol}),
                )
            )
            ratios = _first_list_item(
                self._cached_list(
                    symbol=symbol,
                    dataset="ratios",
                    cache_key="latest",
                    ttl=timedelta(hours=24),
                    fetch=lambda: self._get_list(
                        "/ratios", {"symbol": symbol, "limit": 1}
                    ),
                )
            )
            income_statement = _first_list_item(
                self._cached_list(
                    symbol=symbol,
                    dataset="income_statement",
                    cache_key="latest",
                    ttl=timedelta(days=7),
                    fetch=lambda: self._get_list(
                        "/income-statement", {"symbol": symbol, "limit": 1}
                    ),
                )
            )
            estimates = self._cached_list(
                symbol=symbol,
                dataset="analyst_estimates",
                cache_key="latest",
                ttl=timedelta(hours=12),
                fetch=lambda: self._get_list(
                    "/analyst-estimates", {"symbol": symbol, "limit": 4}
                ),
            )
            ratings = self._cached_list(
                symbol=symbol,
                dataset="ratings_snapshot",
                cache_key="latest",
                ttl=timedelta(hours=12),
                fetch=lambda: self._get_list("/ratings-snapshot", {"symbol": symbol}),
            )
            transcript_dates = self._cached_list(
                symbol=symbol,
                dataset="transcript_dates",
                cache_key="latest",
                ttl=timedelta(hours=24),
                fetch=lambda: self._get_list(
                    "/earning-call-transcript-dates", {"symbol": symbol}
                ),
            )
            transcripts = self._load_transcripts(symbol, transcript_dates[:2])
        except httpx.HTTPError:
            return self._empty_snapshot()

        raw_data = _compact_payload(
            {
                "profile": profile,
                "ratios": ratios,
                "incomeStatement": income_statement,
                "analystEstimates": estimates[:4],
                "analystRatings": ratings[:3],
                "transcriptSummaries": transcripts,
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
            cache_hits=self.cache.cache_hits,
            cache_misses=self.cache.cache_misses,
            stale_fallback_used=self.cache.stale_fallback_used,
            provider_breakdown=self.cache.provider_breakdown,
        )

    def _empty_snapshot(self) -> FundamentalResearchSnapshot:
        return FundamentalResearchSnapshot(
            source=self.provider_name,
            cache_hits=self.cache.cache_hits,
            cache_misses=self.cache.cache_misses,
            stale_fallback_used=self.cache.stale_fallback_used,
            provider_breakdown=self.cache.provider_breakdown,
        )

    def _cached_list(
        self,
        *,
        symbol: str,
        dataset: str,
        cache_key: str,
        ttl: timedelta | None,
        fetch: Callable[[], list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        payload = self.cache.load(
            provider=self.provider_name,
            symbol=symbol,
            dataset=dataset,
            cache_key=cache_key,
            ttl=ttl,
            fetch=fetch,
        )
        return _dict_items(payload)

    def _load_transcripts(
        self, symbol: str, transcript_dates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        for item in transcript_dates:
            year = item.get("year")
            quarter = item.get("quarter")
            if year is None or quarter is None:
                continue
            cache_key = f"{year}:Q{quarter}"
            transcripts = self._cached_list(
                symbol=symbol,
                dataset="transcript_content",
                cache_key=cache_key,
                ttl=None,
                fetch=lambda year=year, quarter=quarter: self._get_list(
                    "/earning-call-transcript",
                    {"symbol": symbol, "year": year, "quarter": quarter},
                ),
            )
            summaries.extend(
                _transcript_summary(transcript)
                for transcript in transcripts[:1]
                if isinstance(transcript, dict)
            )
        return summaries

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


class YahooSentimentResearchProvider:
    provider_name = "yahoo"

    def __init__(
        self,
        *,
        base_url: str = "https://query1.finance.yahoo.com",
        timeout_seconds: int = 10,
        news_lookback_hours: int = 24,
        news_limit: int = 20,
        cache: ResearchCache | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.news_lookback_hours = news_lookback_hours
        self.news_limit = news_limit
        self.client = client or httpx.Client(timeout=timeout_seconds)
        self.cache = cache or ResearchCache()

    def load(self, context: AgentContext) -> SentimentResearchSnapshot:
        return self.load_sentiment(context)

    def load_sentiment(self, context: AgentContext) -> SentimentResearchSnapshot:
        symbol = context.symbol.upper()
        try:
            search_payload = self._cached_object(
                symbol=symbol,
                dataset="yahoo_news",
                cache_key=f"lookback:{self.news_lookback_hours}:limit:{self.news_limit}",
                ttl=timedelta(minutes=30),
                fetch=lambda: self._get_object(
                    "/v1/finance/search",
                    {"q": symbol, "quotesCount": 0, "newsCount": self.news_limit},
                ),
            )
            analyst_payload = self._cached_object(
                symbol=symbol,
                dataset="yahoo_recommendation_trend",
                cache_key="latest",
                ttl=timedelta(hours=12),
                fetch=lambda: self._quote_summary(symbol, ("recommendationTrend",)),
            )
        except httpx.HTTPError:
            return self._empty_snapshot()

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
            cache_hits=self.cache.cache_hits,
            cache_misses=self.cache.cache_misses,
            stale_fallback_used=self.cache.stale_fallback_used,
            provider_breakdown=self.cache.provider_breakdown,
        )

    def _empty_snapshot(self) -> SentimentResearchSnapshot:
        return SentimentResearchSnapshot(
            source=self.provider_name,
            cache_hits=self.cache.cache_hits,
            cache_misses=self.cache.cache_misses,
            stale_fallback_used=self.cache.stale_fallback_used,
            provider_breakdown=self.cache.provider_breakdown,
        )

    def _cached_object(
        self,
        *,
        symbol: str,
        dataset: str,
        cache_key: str,
        ttl: timedelta | None,
        fetch: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        payload = self.cache.load(
            provider=self.provider_name,
            symbol=symbol,
            dataset=dataset,
            cache_key=cache_key,
            ttl=ttl,
            fetch=fetch,
        )
        return _dict_or_empty(payload)

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


def create_research_provider(
    settings: Settings, session: Session | None = None
) -> CompositeResearchProvider:
    if settings.research_data_provider == "fmp" and settings.fmp_api_key:
        fundamental_provider = FmpFundamentalResearchProvider(
            api_key=settings.fmp_api_key,
            base_url=settings.fmp_base_url,
            timeout_seconds=settings.fmp_request_timeout_seconds,
            cache=ResearchCache(session),
        )
        sentiment_provider = YahooSentimentResearchProvider(
            base_url=settings.yahoo_base_url,
            timeout_seconds=settings.yahoo_request_timeout_seconds,
            news_lookback_hours=settings.multi_agent_news_lookback_hours,
            news_limit=settings.multi_agent_news_limit,
            cache=ResearchCache(session),
        )
        return CompositeResearchProvider(fundamental_provider, sentiment_provider)
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


def _first_list_item(items: list[dict[str, Any]]) -> dict[str, Any]:
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
        key = _string_or_none(item.get("url") or item.get("link")) or headline.lower()
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        items.append(
            {
                "headline": headline,
                "publishedAt": item.get("publishedDate")
                or item.get("date")
                or item.get("providerPublishTime"),
                "source": item.get("site") or item.get("publisher") or "Yahoo Finance",
                "url": item.get("url") or item.get("link"),
                "snippet": _truncate(
                    _string_or_none(item.get("text") or item.get("summary")), 500
                ),
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


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dict_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []
