from datetime import datetime, timedelta

import pytest

from app.core.config import get_settings
from app.persistence.database import create_session_factory
from app.persistence.database import get_database_url
from app.persistence.repositories import ResearchDataCacheRepository


def _database_url() -> str:
    settings = get_settings()
    database_url = settings.test_database_url or settings.database_url
    if not database_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL is required.")
    return get_database_url(database_url)


def test_research_data_cache_fresh_expired_stale_and_upsert(
) -> None:
    session_factory = create_session_factory(_database_url())
    now = datetime(2026, 1, 2, 12, 0, 0)

    with session_factory() as session:
        repository = ResearchDataCacheRepository(session)
        repository.upsert(
            provider="fmp",
            symbol="RCRP1",
            dataset="profile",
            cache_key="latest",
            payload_json={"value": 1},
            fetched_at=now,
            expires_at=now + timedelta(days=1),
        )

        fresh = repository.get_fresh(
            provider="fmp",
            symbol="RCRP1",
            dataset="profile",
            cache_key="latest",
            now=now,
        )
        assert fresh is not None
        assert fresh.payload_json == {"value": 1}

        repository.upsert(
            provider="fmp",
            symbol="RCRP1",
            dataset="profile",
            cache_key="latest",
            payload_json={"value": 2},
            fetched_at=now,
            expires_at=now - timedelta(seconds=1),
        )

        expired = repository.get_fresh(
            provider="fmp",
            symbol="RCRP1",
            dataset="profile",
            cache_key="latest",
            now=now,
        )
        stale = repository.get_latest_stale(
            provider="fmp",
            symbol="RCRP1",
            dataset="profile",
            cache_key="latest",
        )

        assert expired is None
        assert stale is not None
        assert stale.payload_json == {"value": 2}
