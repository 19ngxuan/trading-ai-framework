from datetime import datetime
from typing import Any

import httpx

from app.modules.events.types import NewsArticle
from app.modules.market_data.errors import MarketDataProviderError


class AlpacaNewsProvider:
    provider_name = "alpaca"

    def __init__(
        self,
        *,
        api_key_id: str,
        api_secret_key: str,
        base_url: str = "https://data.alpaca.markets",
        timeout_seconds: int = 10,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key_id = api_key_id
        self.api_secret_key = api_secret_key
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=timeout_seconds)

    def fetch_news(
        self,
        *,
        symbols: list[str],
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[NewsArticle]:
        if not symbols:
            return []
        articles: list[NewsArticle] = []
        page_token: str | None = None
        while True:
            params: dict[str, Any] = {
                "symbols": ",".join(sorted({symbol.upper() for symbol in symbols})),
                "start": start.isoformat(),
                "end": end.isoformat(),
                "sort": "desc",
                "limit": limit,
                "include_content": "false",
                "exclude_contentless": "false",
            }
            if page_token:
                params["page_token"] = page_token
            response = self._get("/v1beta1/news", params=params)
            payload = self._json(response)
            raw_news = payload.get("news", [])
            if not isinstance(raw_news, list):
                raise MarketDataProviderError(
                    "Alpaca news response is malformed.",
                    details={"payload": payload},
                )
            articles.extend(self._article(item) for item in raw_news)
            page_token = payload.get("next_page_token")
            if not page_token:
                break
        return articles

    def _get(self, path: str, params: dict[str, Any]) -> httpx.Response:
        try:
            response = self.client.get(
                f"{self.base_url}{path}",
                headers={
                    "APCA-API-KEY-ID": self.api_key_id,
                    "APCA-API-SECRET-KEY": self.api_secret_key,
                },
                params=params,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            raise MarketDataProviderError(
                "Alpaca news request failed.",
                details={
                    "statusCode": exc.response.status_code,
                    "responseText": exc.response.text,
                },
            ) from exc
        except httpx.HTTPError as exc:
            raise MarketDataProviderError(
                "Alpaca news request failed.",
                details={"error": str(exc)},
            ) from exc

    def _json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise MarketDataProviderError(
                "Alpaca news response was not valid JSON.",
                details={"responseText": response.text},
            ) from exc
        if not isinstance(payload, dict):
            raise MarketDataProviderError(
                "Alpaca news response is malformed.",
                details={"payload": payload},
            )
        return payload

    def _article(self, payload: dict[str, Any]) -> NewsArticle:
        if not isinstance(payload, dict):
            raise MarketDataProviderError("Alpaca news item is malformed.")
        symbols = payload.get("symbols") or []
        if not isinstance(symbols, list):
            symbols = []
        return NewsArticle(
            provider=self.provider_name,
            external_event_id=str(payload.get("id") or payload.get("url")),
            timestamp=self._parse_timestamp(payload.get("created_at")),
            updated_at=self._parse_optional_timestamp(payload.get("updated_at")),
            headline=str(payload.get("headline") or ""),
            source=payload.get("source"),
            url=payload.get("url"),
            summary=payload.get("summary"),
            symbols=tuple(str(symbol).upper() for symbol in symbols),
            raw_payload=payload,
        )

    def _parse_optional_timestamp(self, value: Any) -> datetime | None:
        if value is None:
            return None
        return self._parse_timestamp(value)

    def _parse_timestamp(self, value: Any) -> datetime:
        if not isinstance(value, str):
            raise MarketDataProviderError(
                "Alpaca news item is missing a timestamp.",
                details={"value": value},
            )
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(
            tzinfo=None
        )
