from datetime import datetime

import httpx

from app.modules.events.alpaca_news_provider import AlpacaNewsProvider


def test_alpaca_news_provider_builds_expected_request() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "news": [
                    {
                        "id": 123,
                        "created_at": "2026-01-02T15:30:00Z",
                        "updated_at": "2026-01-02T15:31:00Z",
                        "headline": "AAPL receives analyst upgrade",
                        "source": "wire",
                        "url": "https://example.test/news/123",
                        "summary": "Upgrade summary",
                        "symbols": ["AAPL"],
                    }
                ]
            },
        )

    provider = AlpacaNewsProvider(
        api_key_id="key",
        api_secret_key="secret",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    articles = provider.fetch_news(
        symbols=["AAPL"],
        start=datetime(2026, 1, 2, 15, 0),
        end=datetime(2026, 1, 2, 16, 0),
        limit=50,
    )

    assert len(articles) == 1
    assert articles[0].external_event_id == "123"
    assert requests[0].url.path == "/v1beta1/news"
    assert requests[0].url.params["symbols"] == "AAPL"
    assert requests[0].url.params["limit"] == "50"
    assert requests[0].headers["APCA-API-KEY-ID"] == "key"
