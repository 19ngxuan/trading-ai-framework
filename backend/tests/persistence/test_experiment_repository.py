from datetime import date, datetime
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from app.core.config import get_settings
from app.domain.enums import (
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    StrategyType,
    TradingFrequency,
)
from app.persistence.database import create_session_factory, get_database_url
from app.persistence.models import ExperimentModel
from app.persistence.repositories import ExperimentRepository


def _database_url() -> str:
    settings = get_settings()
    database_url = settings.test_database_url or settings.database_url
    if not database_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL is required for database tests.")
    return get_database_url(database_url)


def _require_database() -> str:
    database_url = _database_url()
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect():
            pass
    finally:
        engine.dispose()
    return database_url


def _alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_experiment_repository_saves_and_loads_experiment() -> None:
    database_url = _require_database()
    command.upgrade(_alembic_config(database_url), "head")

    session_factory = create_session_factory(database_url)
    created_at = datetime(2026, 1, 1, 12, 0, 0)

    with session_factory() as session:
        repository = ExperimentRepository(session)
        experiment = repository.add(
            ExperimentModel(
                name=f"M1 repository smoke {created_at.isoformat()}",
                mode=ExperimentMode.HISTORICAL_SIMULATION,
                strategy_type=StrategyType.BUY_AND_HOLD,
                asset_symbol="SPY",
                status=ExperimentStatus.CREATED,
                initial_capital=Decimal("10000.0000"),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                trading_frequency=TradingFrequency.DAILY,
                fee_model_type=FeeModelType.NONE,
                fee_value=Decimal("0.00000000"),
                created_at=created_at,
                updated_at=created_at,
            )
        )
        session.commit()
        experiment_id = experiment.id

    with session_factory() as session:
        repository = ExperimentRepository(session)
        loaded = repository.get_by_id(experiment_id)

        assert loaded is not None
        assert loaded.asset_symbol == "SPY"
        assert loaded.mode is ExperimentMode.HISTORICAL_SIMULATION
        assert loaded.strategy_type is StrategyType.BUY_AND_HOLD
        assert loaded.status is ExperimentStatus.CREATED
