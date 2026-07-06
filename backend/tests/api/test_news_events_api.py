from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.enums import (
    EventDecisionStatus,
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    ImpactDirection,
    NewsEventSeverity,
    NewsEventType,
    StrategyType,
    TradingFrequency,
)
from app.persistence.database import create_session_factory
from app.persistence.models import (
    EventAssetImpactModel,
    EventDecisionModel,
    ExperimentModel,
    NewsEventModel,
    PortfolioModel,
    StrategyConfigModel,
)


def _create_experiment(session: Session) -> int:
    now = datetime(2026, 1, 1, 12, 0, 0)
    experiment = ExperimentModel(
        name="Event Agent",
        mode=ExperimentMode.PAPER_TRADING,
        strategy_type=StrategyType.AGENTIC_AI,
        asset_symbol="AAPL",
        status=ExperimentStatus.RUNNING,
        initial_capital=Decimal("10000.0000"),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
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
            strategy_type=StrategyType.AGENTIC_AI,
            moving_average_window=None,
            agent_mode=None,
            model_name=None,
            confidence_threshold=Decimal("0.7000"),
            parameters_json={},
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
    return experiment.id


def _add_news_event(session: Session, experiment_id: int) -> int:
    now = datetime(2026, 1, 1, 12, 0, 0)
    event = NewsEventModel(
        provider="alpaca",
        external_event_id="evt-1",
        timestamp=now,
        updated_at=None,
        headline="AAPL receives analyst upgrade",
        source="wire",
        url="https://example.test/evt-1",
        summary="Analyst upgrade summary.",
        event_type=NewsEventType.ANALYST_UPGRADE,
        severity=NewsEventSeverity.MEDIUM,
        affected_symbols_json=["AAPL"],
        raw_payload_json={"id": "evt-1"},
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
    )
    session.add(event)
    session.flush()
    session.add(
        EventAssetImpactModel(
            event_id=event.id,
            symbol="AAPL",
            impact_direction=ImpactDirection.POSITIVE,
            relevance_score=Decimal("0.8500"),
            rationale="Relevant upgrade.",
            raw_impact_json={"classifier": "test"},
            created_at=now,
        )
    )
    session.add(
        EventDecisionModel(
            event_id=event.id,
            experiment_id=experiment_id,
            execution_step_id=None,
            trading_decision_id=None,
            status=EventDecisionStatus.TRIGGERED,
            reason="Queued.",
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()
    return event.id


def test_news_events_are_listed_and_filterable(client, migrated_database: str) -> None:
    session_factory = create_session_factory(migrated_database)
    with session_factory() as session:
        experiment_id = _create_experiment(session)
        event_id = _add_news_event(session, experiment_id)

    response = client.get("/api/v1/news-events?symbol=AAPL&eventType=ANALYST_UPGRADE")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == event_id
    assert payload["items"][0]["affectedSymbols"] == ["AAPL"]


def test_experiment_event_decisions_are_read_only(client, migrated_database: str) -> None:
    session_factory = create_session_factory(migrated_database)
    with session_factory() as session:
        experiment_id = _create_experiment(session)
        _add_news_event(session, experiment_id)

    response = client.get(f"/api/v1/experiments/{experiment_id}/event-decisions")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["status"] == "TRIGGERED"
