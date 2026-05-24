from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.enums import (
    EventLevel,
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    StrategyType,
    SystemEventType,
    TradingFrequency,
)
from app.persistence.database import create_session_factory
from app.persistence.models import (
    ExperimentModel,
    PortfolioModel,
    StrategyConfigModel,
    SystemEventLogModel,
)


def _create_experiment(session: Session, name: str) -> int:
    now = datetime(2026, 1, 1, 12, 0, 0)
    experiment = ExperimentModel(
        name=name,
        mode=ExperimentMode.HISTORICAL_SIMULATION,
        strategy_type=StrategyType.BUY_AND_HOLD,
        asset_symbol="SPY",
        status=ExperimentStatus.CREATED,
        initial_capital=Decimal("10000.0000"),
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 5),
        trading_frequency=TradingFrequency.DAILY,
        fee_model_type=FeeModelType.NONE,
        fee_value=Decimal("0"),
        created_at=now,
        updated_at=now,
    )
    session.add(experiment)
    session.flush()
    session.add(
        StrategyConfigModel(
            experiment_id=experiment.id,
            strategy_type=StrategyType.BUY_AND_HOLD,
            strategy_version="buy-and-hold-v1",
            moving_average_window=None,
            position_sizing_type="ALL_IN",
            agent_mode=None,
            model_name=None,
            confidence_threshold=None,
            parameters_json={"riskConfig": {"fallbackAction": "HOLD"}},
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        PortfolioModel(
            experiment_id=experiment.id,
            cash=Decimal("10000.0000"),
            position_symbol=None,
            position_quantity=Decimal("0"),
            current_price=None,
            current_position_value=Decimal("0"),
            current_portfolio_value=Decimal("10000.0000"),
            updated_at=now,
        )
    )
    session.commit()
    return experiment.id


def _add_event(
    session: Session,
    *,
    experiment_id: int,
    timestamp: datetime,
    level: EventLevel,
    event_type: SystemEventType,
    message: str,
) -> None:
    session.add(
        SystemEventLogModel(
            execution_step_id=None,
            experiment_id=experiment_id,
            timestamp=timestamp,
            level=level,
            event_type=event_type,
            message=message,
            details_json={"message": message},
            created_at=timestamp,
        )
    )


def test_global_events_are_ordered_desc_and_paginated(
    client, migrated_database: str
) -> None:
    session_factory = create_session_factory(migrated_database)
    base_time = datetime(2026, 1, 1, 12, 0, 0)
    with session_factory() as session:
        experiment_id = _create_experiment(session, "Events")
        _add_event(
            session,
            experiment_id=experiment_id,
            timestamp=base_time,
            level=EventLevel.INFO,
            event_type=SystemEventType.EXPERIMENT_CREATED,
            message="old",
        )
        _add_event(
            session,
            experiment_id=experiment_id,
            timestamp=base_time + timedelta(minutes=1),
            level=EventLevel.ERROR,
            event_type=SystemEventType.EXPERIMENT_FAILED,
            message="new",
        )
        session.commit()

    response = client.get("/api/v1/events?limit=1&offset=0")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["items"][0]["message"] == "new"
    assert body["items"][0]["level"] == "ERROR"
    assert body["items"][0]["eventType"] == "EXPERIMENT_FAILED"


def test_global_events_filter_by_experiment_level_and_event_type(
    client, migrated_database: str
) -> None:
    session_factory = create_session_factory(migrated_database)
    now = datetime(2026, 1, 1, 12, 0, 0)
    with session_factory() as session:
        first_id = _create_experiment(session, "First")
        second_id = _create_experiment(session, "Second")
        _add_event(
            session,
            experiment_id=first_id,
            timestamp=now,
            level=EventLevel.ERROR,
            event_type=SystemEventType.EXPERIMENT_FAILED,
            message="first failed",
        )
        _add_event(
            session,
            experiment_id=second_id,
            timestamp=now + timedelta(minutes=1),
            level=EventLevel.INFO,
            event_type=SystemEventType.EXPERIMENT_CREATED,
            message="second created",
        )
        session.commit()

    response = client.get(
        f"/api/v1/events?experimentId={first_id}&level=ERROR&eventType=EXPERIMENT_FAILED"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["experimentId"] == first_id
    assert body["items"][0]["detailsJson"] == {"message": "first failed"}


def test_experiment_scoped_events_and_missing_experiment(
    client, migrated_database: str
) -> None:
    session_factory = create_session_factory(migrated_database)
    now = datetime(2026, 1, 1, 12, 0, 0)
    with session_factory() as session:
        experiment_id = _create_experiment(session, "Scoped")
        _add_event(
            session,
            experiment_id=experiment_id,
            timestamp=now,
            level=EventLevel.WARNING,
            event_type=SystemEventType.RISK_LIMIT_TRIGGERED,
            message="risk warning",
        )
        session.commit()

    response = client.get(f"/api/v1/experiments/{experiment_id}/events")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["level"] == "WARNING"
    assert body["items"][0]["eventType"] == "RISK_LIMIT_TRIGGERED"

    missing = client.get("/api/v1/experiments/9999/events")
    assert missing.status_code == 404
    assert missing.json()["errorCode"] == "EXPERIMENT_NOT_FOUND"
