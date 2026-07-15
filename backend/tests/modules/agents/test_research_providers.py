from datetime import date
from decimal import Decimal

import httpx

from app.domain.enums import AgentMode
from app.modules.agents.provider_factory import FmpResearchProvider
from app.modules.agents.types import AgentContext
from app.modules.market_data.provider import DailyBar


def _context() -> AgentContext:
    return AgentContext(
        experiment_id=1,
        execution_step_id=1,
        symbol="AAPL",
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


def test_fmp_research_provider_normalizes_fundamentals_and_sentiment() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
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
        if request.url.path.endswith("/news/stock"):
            return httpx.Response(
                200,
                json=[
                    {
                        "title": "Apple announces product update",
                        "publishedDate": "2026-01-02",
                        "site": "Example Wire",
                        "url": "https://example.test/news/1",
                        "text": "Positive product news.",
                    },
                    {
                        "title": "Apple announces product update duplicate",
                        "publishedDate": "2026-01-02",
                        "site": "Example Wire",
                        "url": "https://example.test/news/1",
                    },
                ],
            )
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

    provider = FmpResearchProvider(
        api_key="key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    fundamentals = provider.load_fundamental(_context())
    sentiment = provider.load_sentiment(_context())

    assert fundamentals.data_available is True
    assert fundamentals.pe_ratio == Decimal("30.5")
    assert fundamentals.market_cap == Decimal("3000000000000")
    assert fundamentals.analyst_estimates is not None
    assert sentiment.news_available is True
    assert sentiment.transcript_available is True
    assert sentiment.duplicate_count == 1
    assert sentiment.headlines == ("Apple announces product update",)


def test_fmp_research_provider_returns_empty_snapshots_on_http_error() -> None:
    provider = FmpResearchProvider(
        api_key="key",
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(500))
        ),
    )

    fundamentals = provider.load_fundamental(_context())
    sentiment = provider.load_sentiment(_context())

    assert fundamentals.data_available is False
    assert sentiment.news_available is False
    assert sentiment.transcript_available is False
