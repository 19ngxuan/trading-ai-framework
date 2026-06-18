from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import (
    EventLevel,
    ExecutionStepStatus,
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    StrategyType,
    SystemEventType,
    TradingFrequency,
    TriggerType,
)
from app.persistence.database import create_session_factory
from app.persistence.models import (
    ExecutionStepModel,
    ExperimentModel,
    MetricSnapshotModel,
    PortfolioModel,
    StrategyConfigModel,
    SystemEventLogModel,
)


def _create_experiment(
    session: Session,
    *,
    name: str,
    total_return: Decimal | None,
    current_portfolio_value: Decimal = Decimal("10000.0000"),
) -> int:
    now = datetime(2026, 1, 1, 12, 0, 0)
    experiment = ExperimentModel(
        name=name,
        mode=ExperimentMode.HISTORICAL_SIMULATION,
        strategy_type=StrategyType.BUY_AND_HOLD,
        asset_symbol="SPY",
        status=ExperimentStatus.COMPLETED,
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
            moving_average_window=None,
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
            cash=current_portfolio_value,
            position_symbol=None,
            position_quantity=Decimal("0"),
            current_price=None,
            current_position_value=Decimal("0"),
            current_portfolio_value=current_portfolio_value,
            updated_at=now,
        )
    )
    if total_return is not None:
        step = ExecutionStepModel(
            experiment_id=experiment.id,
            scheduled_for=now,
            started_at=now,
            completed_at=now,
            status=ExecutionStepStatus.COMPLETED,
            trigger_type=TriggerType.MANUAL,
            sequence_number=1,
            error_message=None,
            created_at=now,
        )
        session.add(step)
        session.flush()
        session.add(
            MetricSnapshotModel(
                execution_step_id=step.id,
                experiment_id=experiment.id,
                timestamp=now,
                total_return=total_return,
                profit_loss=Decimal("1000.0000"),
                number_of_trades=1,
                max_drawdown=Decimal("-0.05000000"),
                buy_and_hold_return=total_return,
                difference_to_buy_and_hold=Decimal("0"),
                created_at=now,
            )
        )
    session.add(
        SystemEventLogModel(
            execution_step_id=None,
            experiment_id=experiment.id,
            timestamp=now,
            level=EventLevel.INFO,
            event_type=SystemEventType.EXPERIMENT_CREATED,
            message=f"{name} created.",
            details_json={"experimentId": experiment.id},
            created_at=now,
        )
    )
    session.commit()
    return experiment.id


def test_compare_multiple_experiments_with_benchmark_difference(
    client, migrated_database: str
) -> None:
    session_factory = create_session_factory(migrated_database)
    with session_factory() as session:
        benchmark_id = _create_experiment(
            session, name="Benchmark", total_return=Decimal("0.05000000")
        )
        candidate_id = _create_experiment(
            session,
            name="Candidate",
            total_return=Decimal("0.12000000"),
            current_portfolio_value=Decimal("11200.0000"),
        )

    response = client.post(
        "/api/v1/experiments/compare",
        json={
            "experimentIds": [benchmark_id, candidate_id],
            "benchmarkExperimentId": benchmark_id,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["benchmarkExperimentId"] == benchmark_id
    candidate = next(
        item for item in body["items"] if item["experimentId"] == candidate_id
    )
    assert candidate["latestPortfolioValue"] == 11200.0
    assert candidate["totalReturn"] == 0.12
    assert candidate["profitLoss"] == 1000.0
    assert candidate["numberOfTrades"] == 1
    assert candidate["maxDrawdown"] == -0.05
    assert candidate["benchmarkReturn"] == 0.05
    assert candidate["differenceToBenchmark"] == 0.07


def test_compare_without_benchmark_returns_null_benchmark_fields(
    client, migrated_database: str
) -> None:
    session_factory = create_session_factory(migrated_database)
    with session_factory() as session:
        first_id = _create_experiment(
            session, name="First", total_return=Decimal("0.01000000")
        )
        second_id = _create_experiment(
            session, name="Second", total_return=Decimal("0.02000000")
        )

    response = client.post(
        "/api/v1/experiments/compare",
        json={"experimentIds": [first_id, second_id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["benchmarkExperimentId"] is None
    assert all(item["benchmarkReturn"] is None for item in body["items"])
    assert all(item["differenceToBenchmark"] is None for item in body["items"])


def test_compare_validation_errors(client, migrated_database: str) -> None:
    session_factory = create_session_factory(migrated_database)
    with session_factory() as session:
        first_id = _create_experiment(
            session, name="First", total_return=Decimal("0.01000000")
        )
        second_id = _create_experiment(
            session, name="Second", total_return=Decimal("0.02000000")
        )

    cases = [
        {"experimentIds": [first_id]},
        {"experimentIds": [first_id, first_id]},
        {"experimentIds": [first_id, second_id], "benchmarkExperimentId": 9999},
    ]
    for payload in cases:
        response = client.post("/api/v1/experiments/compare", json=payload)
        assert response.status_code == 422
        assert response.json()["errorCode"] == "VALIDATION_ERROR"


def test_compare_missing_experiment_returns_404(client, migrated_database: str) -> None:
    session_factory = create_session_factory(migrated_database)
    with session_factory() as session:
        experiment_id = _create_experiment(
            session, name="Existing", total_return=Decimal("0.01000000")
        )

    response = client.post(
        "/api/v1/experiments/compare",
        json={"experimentIds": [experiment_id, 9999]},
    )

    assert response.status_code == 404
    assert response.json()["errorCode"] == "EXPERIMENT_NOT_FOUND"


def test_compare_missing_metrics_returns_nulls(client, migrated_database: str) -> None:
    session_factory = create_session_factory(migrated_database)
    with session_factory() as session:
        first_id = _create_experiment(session, name="No Metrics", total_return=None)
        second_id = _create_experiment(
            session, name="With Metrics", total_return=Decimal("0.03000000")
        )

    response = client.post(
        "/api/v1/experiments/compare",
        json={"experimentIds": [first_id, second_id]},
    )

    assert response.status_code == 200
    item = next(
        item for item in response.json()["items"] if item["experimentId"] == first_id
    )
    assert item["totalReturn"] is None
    assert item["profitLoss"] is None
    assert item["numberOfTrades"] is None
    assert item["maxDrawdown"] is None

    with session_factory() as session:
        assert (
            session.scalar(
                select(MetricSnapshotModel).where(
                    MetricSnapshotModel.experiment_id == first_id
                )
            )
            is None
        )
