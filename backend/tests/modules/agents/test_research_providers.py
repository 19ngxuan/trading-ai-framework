from datetime import date, datetime
from decimal import Decimal

import httpx

from app.core.config import Settings
from app.domain.enums import AgentMode
from app.modules.agents.provider_factory import (
    FmpFundamentalResearchProvider,
    ResearchCache,
    YahooSentimentResearchProvider,
    create_research_provider,
)
from app.modules.agents.types import AgentContext
from app.modules.market_data.provider import DailyBar
from app.persistence.database import create_session_factory
from app.persistence.repositories import ResearchDataCacheRepository


def _context(symbol: str = "AAPL") -> AgentContext:
    return AgentContext(
        experiment_id=1,
        execution_step_id=1,
        symbol=symbol,
        bar=DailyBar(
            date=date(2026, 1, 2),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            adjusted_close=Decimal("100"),
            volume=Decimal("1000000"),
            raw={},
        ),
        cash=Decimal("10000"),
        position_quantity=Decimal("0"),
        current_portfolio_value=Decimal("10000"),
        confidence_threshold=None,
        parameters_json=None,
        agent_mode=AgentMode.PIPELINE,
        model_name=None,
    )


def test_create_research_provider_splits_fmp_fundamentals_and_yahoo_sentiment() -> None:
    provider = create_research_provider(
        Settings(
            research_data_provider="fmp",
            fmp_api_key="key",
            scadsai_llm_enabled=False,
        )
    )

    assert isinstance(provider.fundamental_provider, FmpFundamentalResearchProvider)
    assert isinstance(provider.sentiment_provider, YahooSentimentResearchProvider)


def test_fmp_fundamental_provider_caches_symbol_datasets(database_url: str) -> None:
    symbol = "RCFMP1"
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path.endswith("/profile"):
            return httpx.Response(
                200,
                json=[
                    {
                        "symbol": "AAPL",
                        "marketCap": 3000000000000,
                        "description": "Consumer technology company.",
                    }
                ],
            )
        if request.url.path.endswith("/ratios"):
            return httpx.Response(
                200,
                json=[
                    {
                        "priceEarningsRatio": 30.5,
                        "netProfitMargin": 0.25,
                        "revenueGrowth": 0.08,
                    }
                ],
            )
        if request.url.path.endswith("/income-statement"):
            return httpx.Response(200, json=[{"revenue": 1000}])
        if request.url.path.endswith("/analyst-estimates"):
            return httpx.Response(200, json=[{"estimatedPeAvg": 28.1}])
        if request.url.path.endswith("/ratings-snapshot"):
            return httpx.Response(200, json=[{"rating": "Buy"}])
        if request.url.path.endswith("/earning-call-transcript-dates"):
            return httpx.Response(200, json=[{"quarter": 1, "year": 2026}])
        if request.url.path.endswith("/earning-call-transcript"):
            return httpx.Response(
                200,
                json=[
                    {"quarter": 1, "year": 2026, "content": "Prepared remarks."}
                ],
            )
        return httpx.Response(404)

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        cache = ResearchCache(session)
        provider = FmpFundamentalResearchProvider(
            api_key="key",
            cache=cache,
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )

        first = provider.load_fundamental(_context(symbol))
        second = provider.load_fundamental(_context(symbol))

        assert first.data_available is True
        assert second.data_available is True
        assert second.cache_hits >= 7
        assert second.cache_misses == 7
        assert _request_count(requests, "/profile") == 1
        assert _request_count(requests, "/ratios") == 1
        assert _request_count(requests, "/earning-call-transcript") == 1

        repository = ResearchDataCacheRepository(session)
        transcript_cache = repository.get_latest_stale(
            provider="fmp",
            symbol=symbol,
            dataset="transcript_content",
            cache_key="2026:Q1",
        )
        assert transcript_cache is not None
        assert transcript_cache.expires_at is None


def test_yahoo_sentiment_provider_caches_news_separately(database_url: str) -> None:
    symbol = "RCYH1"
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path.endswith("/search"):
            return httpx.Response(
                200,
                json={
                    "news": [
                        {
                            "title": "Apple announces product update",
                            "providerPublishTime": 1767355200,
                            "publisher": "Example Wire",
                            "link": "https://example.test/news/1",
                            "summary": "Positive product news.",
                        },
                        {
                            "title": "Apple announces duplicate",
                            "providerPublishTime": 1767355200,
                            "publisher": "Example Wire",
                            "link": "https://example.test/news/1",
                        },
                    ]
                },
            )
        if request.url.path.endswith(f"/quoteSummary/{symbol}"):
            return httpx.Response(
                200,
                json={
                    "quoteSummary": {
                        "result": [
                            {
                                "recommendationTrend": {
                                    "trend": [{"period": "0m", "strongBuy": 10}]
                                }
                            }
                        ],
                        "error": None,
                    }
                },
            )
        return httpx.Response(404)

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        cache = ResearchCache(session)
        provider = YahooSentimentResearchProvider(
            cache=cache,
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )

        first = provider.load_sentiment(_context(symbol))
        second = provider.load_sentiment(_context(symbol))

        assert first.news_available is True
        assert first.transcript_available is False
        assert first.duplicate_count == 1
        assert second.cache_hits >= 2
        assert second.cache_misses == 2
        assert requests.count("/v1/finance/search") == 1
        assert requests.count(f"/v10/finance/quoteSummary/{symbol}") == 1


def test_fmp_fundamental_provider_uses_stale_cache_on_provider_error(
    database_url: str,
) -> None:
    symbol = "RCST1"
    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        repository = ResearchDataCacheRepository(session)
        repository.upsert(
            provider="fmp",
            symbol=symbol,
            dataset="profile",
            cache_key="latest",
            payload_json=[{"marketCap": 100, "description": "Cached profile"}],
            fetched_at=datetime(2026, 1, 1, 0, 0, 0),
            expires_at=datetime(2026, 1, 1, 0, 0, 0),
        )

        provider = FmpFundamentalResearchProvider(
            api_key="key",
            cache=ResearchCache(session),
            client=httpx.Client(
                transport=httpx.MockTransport(lambda request: httpx.Response(500))
            ),
        )

        snapshot = provider.load_fundamental(_context(symbol))

        assert snapshot.stale_fallback_used is True
        assert snapshot.cache_hits >= 1


def _request_count(requests: list[str], suffix: str) -> int:
    return sum(1 for request in requests if request.endswith(suffix))
