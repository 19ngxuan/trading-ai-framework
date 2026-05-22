import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings


def _database_url() -> str:
    settings = get_settings()
    database_url = settings.test_database_url or settings.database_url
    if not database_url:
        pytest.skip(
            "TEST_DATABASE_URL or DATABASE_URL is required for migration tests."
        )
    return database_url


def _require_database() -> str:
    database_url = _database_url()
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect():
            pass
    except SQLAlchemyError as exc:
        pytest.skip(f"Database is not reachable for migration tests: {exc}")
    finally:
        engine.dispose()
    return database_url


def _alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_initial_migration_creates_documented_tables_and_trade_cardinality() -> None:
    database_url = _require_database()
    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        inspector = inspect(engine)

        table_names = set(inspector.get_table_names())
        assert {
            "experiments",
            "risk_checks",
            "trades",
            "system_event_logs",
        }.issubset(table_names)

        unique_columns = {
            tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints("trades")
        }
        unique_indexes = {
            tuple(index["column_names"])
            for index in inspector.get_indexes("trades")
            if index.get("unique")
        }

        assert ("order_id",) not in unique_columns
        assert ("execution_step_id",) not in unique_columns
        assert ("order_id",) not in unique_indexes
        assert ("execution_step_id",) not in unique_indexes
    finally:
        engine.dispose()
