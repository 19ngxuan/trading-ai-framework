from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.persistence.models import ResearchDataCacheModel
from app.persistence.repositories.base import BaseRepository


class ResearchDataCacheRepository(BaseRepository[ResearchDataCacheModel]):
    model = ResearchDataCacheModel

    def get_fresh(
        self,
        *,
        provider: str,
        symbol: str,
        dataset: str,
        cache_key: str,
        now: datetime,
    ) -> ResearchDataCacheModel | None:
        statement = self._base_statement(provider, symbol, dataset, cache_key).where(
            (self.model.expires_at.is_(None)) | (self.model.expires_at > now)
        )
        return self.session.scalar(statement)

    def get_latest_stale(
        self,
        *,
        provider: str,
        symbol: str,
        dataset: str,
        cache_key: str,
    ) -> ResearchDataCacheModel | None:
        statement = self._base_statement(provider, symbol, dataset, cache_key)
        return self.session.scalar(statement)

    def upsert(
        self,
        *,
        provider: str,
        symbol: str,
        dataset: str,
        cache_key: str,
        payload_json: dict[str, Any] | list[Any],
        fetched_at: datetime,
        expires_at: datetime | None,
    ) -> ResearchDataCacheModel:
        normalized_symbol = symbol.upper()
        existing = self.session.scalar(
            self._base_statement(provider, normalized_symbol, dataset, cache_key)
        )
        if existing is None:
            existing = ResearchDataCacheModel(
                provider=provider,
                symbol=normalized_symbol,
                dataset=dataset,
                cache_key=cache_key,
                payload_json=payload_json,
                fetched_at=fetched_at,
                expires_at=expires_at,
                created_at=fetched_at,
                updated_at=fetched_at,
            )
            self.session.add(existing)
            self.session.flush()
            return existing

        existing.payload_json = payload_json
        existing.fetched_at = fetched_at
        existing.expires_at = expires_at
        existing.updated_at = fetched_at
        self.session.flush()
        return existing

    def _base_statement(
        self,
        provider: str,
        symbol: str,
        dataset: str,
        cache_key: str,
    ):
        return select(self.model).where(
            self.model.provider == provider,
            self.model.symbol == symbol.upper(),
            self.model.dataset == dataset,
            self.model.cache_key == cache_key,
        )
