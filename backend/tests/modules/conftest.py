from collections.abc import Generator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.persistence.database import get_database_url


def _database_url() -> str:
    settings = get_settings()
    database_url = settings.test_database_url or settings.database_url
    if not database_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL is required for module tests.")
    return get_database_url(database_url)


def _alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> str:
    database_url = _database_url()
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect():
            pass
    finally:
        engine.dispose()
    command.upgrade(_alembic_config(database_url), "head")
    return database_url


@pytest.fixture(autouse=True)
def clean_tables(migrated_database: str) -> Generator[None, None, None]:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE experiments RESTART IDENTITY CASCADE"
            )
        )
    engine.dispose()
    yield


@pytest.fixture
def database_url(migrated_database: str) -> str:
    return migrated_database
