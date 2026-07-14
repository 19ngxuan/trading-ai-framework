from datetime import date
from decimal import Decimal

import httpx

from app.domain.enums import AgentMode
from app.modules.agents.provider_factory import YahooResearchProvider
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


def test_yahoo_research_provider_normalizes_fundamentals_and_sentiment() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/quoteSummary/AAPL"):
            return httpx.Response(
                200,
                json={
                    "quoteSummary": {
                        "result": [
                            {
                                "summaryProfile": {
                                    "longBusinessSummary": (
                                        "Consumer technology company."
                                    )
                                },
                                "summaryDetail": {
                                    "trailingPE": {"raw": 30.5},
                                    "forwardPE": {"raw": 28.1},
                                    "marketCap": {"raw": 3000000000000},
                                    "yield": {"raw": 0.005},
                                },
                                "financialData": {
                                    "profitMargins": {"raw": 0.25},
                                    "revenueGrowth": {"raw": 0.08},
                                },
                                "recommendationTrend": {
                                    "trend": [{"period": "0m", "strongBuy": 10}]
                                },
                                "earningsTrend": {
                                    "trend": [{"period": "0q", "growth": {"raw": 0.1}}]
                                },
                            }
                        ],
                        "error": None,
                    }
                },
            )
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
                            "title": "Apple announces product update duplicate",
                            "providerPublishTime": 1767355200,
                            "publisher": "Example Wire",
                            "link": "https://example.test/news/1",
                        },
                    ]
                },
            )
        return httpx.Response(404)

    provider = YahooResearchProvider(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    fundamentals = provider.load_fundamental(_context())
    sentiment = provider.load_sentiment(_context())

    assert fundamentals.data_available is True
    assert fundamentals.pe_ratio == Decimal("30.5")
    assert fundamentals.market_cap == Decimal("3000000000000")
    assert fundamentals.analyst_estimates is not None
    assert sentiment.news_available is True
    assert sentiment.transcript_available is False
    assert sentiment.duplicate_count == 1
    assert sentiment.headlines == ("Apple announces product update",)


def test_yahoo_research_provider_returns_empty_snapshots_on_http_error() -> None:
    provider = YahooResearchProvider(
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(500))
        ),
    )

    fundamentals = provider.load_fundamental(_context())
    sentiment = provider.load_sentiment(_context())

    assert fundamentals.data_available is False
    assert sentiment.news_available is False
    assert sentiment.transcript_available is False
