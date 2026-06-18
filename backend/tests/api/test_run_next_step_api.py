from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.enums import (
    ExecutionStepStatus,
    ExperimentMode,
    ExperimentStatus,
    FeeModelType,
    StrategyType,
    SystemEventType,
    TriggerType,
    TradingFrequency,
)
from app.persistence.database import get_database_url
from app.persistence.models import (
    ExecutionStepModel,
    ExperimentModel,
    SystemEventLogModel,
)


def _buy_and_hold_payload() -> dict:
    return {
        "name": "M7a Buy and Hold",
        "mode": "HISTORICAL_SIMULATION",
        "strategyType": "BUY_AND_HOLD",
        "assetSymbol": "SPY",
        "initialCapital": 10000,
        "startDate": "2024-01-02",
        "endDate": "2024-01-05",
        "tradingFrequency": "DAILY",
        "feeModelType": "NONE",
        "feeValue": 0,
        "strategyConfig": {
            "movingAverageWindow": None,
            "agentMode": None,
            "modelName": None,
            "confidenceThreshold": None,
            "parametersJson": {"riskConfig": {"fallbackAction": "HOLD"}},
        },
    }


def _moving_average_payload() -> dict:
    payload = _buy_and_hold_payload()
    payload["name"] = "M7a Moving Average"
    payload["strategyType"] = "MOVING_AVERAGE"
    payload["endDate"] = "2024-01-10"
    payload["strategyConfig"] = {
        "movingAverageWindow": 3,
        "agentMode": None,
        "modelName": None,
        "confidenceThreshold": None,
        "parametersJson": {"riskConfig": {"fallbackAction": "HOLD"}},
    }
    return payload


def _database_url() -> str:
    settings = get_settings()
    database_url = settings.test_database_url or settings.database_url
    assert database_url is not None
    return get_database_url(database_url)


def _set_status(experiment_id: int, status: ExperimentStatus) -> None:
    engine = create_engine(_database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        experiment = session.get(ExperimentModel, experiment_id)
        assert experiment is not None
        experiment.status = status
        session.commit()
    engine.dispose()


def _count_steps(experiment_id: int) -> int:
    engine = create_engine(_database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        count = int(
            session.scalar(
                select(func.count(ExecutionStepModel.id)).where(
                    ExecutionStepModel.experiment_id == experiment_id
                )
            )
            or 0
        )
    engine.dispose()
    return count


def _insert_legacy_historical_agentic_experiment(
    status: ExperimentStatus,
) -> int:
    engine = create_engine(_database_url(), pool_pre_ping=True)
    now = datetime(2026, 1, 1, 12, 0, 0)
    with Session(engine) as session:
        experiment = ExperimentModel(
            name="Legacy historical Agentic AI",
            mode=ExperimentMode.HISTORICAL_SIMULATION,
            strategy_type=StrategyType.AGENTIC_AI,
            asset_symbol="SPY",
            status=status,
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
        session.commit()
        experiment_id = experiment.id
    engine.dispose()
    return experiment_id


def test_run_next_step_executes_one_buy_and_hold_bar(client) -> None:
    create_response = client.post("/api/v1/experiments", json=_buy_and_hold_payload())
    experiment_id = create_response.json()["experiment"]["id"]
    _set_status(experiment_id, ExperimentStatus.RUNNING)

    response = client.post(
        f"/api/v1/experiments/{experiment_id}/run-next-step",
        json={"triggerReason": "Manual debug execution"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["experimentId"] == experiment_id
    assert body["executionStepId"] is not None
    assert body["status"] == "COMPLETED"
    assert body["message"] == "Manual execution step completed."

    engine = create_engine(_database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        steps = list(
            session.scalars(
                select(ExecutionStepModel)
                .where(ExecutionStepModel.experiment_id == experiment_id)
                .order_by(ExecutionStepModel.sequence_number)
            )
        )
        assert len(steps) == 1
        assert steps[0].status is ExecutionStepStatus.COMPLETED
        assert steps[0].trigger_type is TriggerType.MANUAL
    engine.dispose()


def test_run_next_step_rejects_legacy_historical_agentic_ai(client) -> None:
    experiment_id = _insert_legacy_historical_agentic_experiment(
        ExperimentStatus.RUNNING
    )

    response = client.post(f"/api/v1/experiments/{experiment_id}/run-next-step")

    assert response.status_code == 409
    assert response.json()["errorCode"] == "INVALID_EXPERIMENT_CONFIGURATION"
    assert _count_steps(experiment_id) == 0


def test_start_rejects_legacy_historical_agentic_ai(client) -> None:
    experiment_id = _insert_legacy_historical_agentic_experiment(
        ExperimentStatus.CREATED
    )

    response = client.post(f"/api/v1/experiments/{experiment_id}/start")

    assert response.status_code == 409
    assert response.json()["errorCode"] == "INVALID_EXPERIMENT_CONFIGURATION"
    assert _count_steps(experiment_id) == 0


def test_run_next_step_after_final_bar_completes_then_rejects(client) -> None:
    payload = _buy_and_hold_payload()
    payload["endDate"] = "2024-01-02"
    create_response = client.post("/api/v1/experiments", json=payload)
    experiment_id = create_response.json()["experiment"]["id"]
    _set_status(experiment_id, ExperimentStatus.RUNNING)

    first_response = client.post(f"/api/v1/experiments/{experiment_id}/run-next-step")
    second_response = client.post(f"/api/v1/experiments/{experiment_id}/run-next-step")

    assert first_response.status_code == 202
    assert first_response.json()["status"] == "COMPLETED"
    assert second_response.status_code == 409
    assert second_response.json()["errorCode"] == "INVALID_EXPERIMENT_STATUS"

    engine = create_engine(_database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        experiment = session.get(ExperimentModel, experiment_id)
        assert experiment is not None
        assert experiment.status is ExperimentStatus.COMPLETED
        event_types = set(
            session.scalars(
                select(SystemEventLogModel.event_type).where(
                    SystemEventLogModel.experiment_id == experiment_id
                )
            )
        )
        assert SystemEventType.EXPERIMENT_COMPLETED in event_types
    engine.dispose()


def test_run_next_step_rejects_non_running_status(client) -> None:
    create_response = client.post("/api/v1/experiments", json=_buy_and_hold_payload())
    experiment_id = create_response.json()["experiment"]["id"]

    response = client.post(f"/api/v1/experiments/{experiment_id}/run-next-step")

    assert response.status_code == 409
    assert response.json()["errorCode"] == "INVALID_EXPERIMENT_STATUS"
    assert _count_steps(experiment_id) == 0


def test_run_next_step_rejects_unsupported_configuration(client) -> None:
    payload = _moving_average_payload()
    payload["tradingFrequency"] = "WEEKLY"
    create_response = client.post("/api/v1/experiments", json=payload)
    experiment_id = create_response.json()["experiment"]["id"]
    _set_status(experiment_id, ExperimentStatus.RUNNING)

    response = client.post(f"/api/v1/experiments/{experiment_id}/run-next-step")

    assert response.status_code == 409
    assert response.json()["errorCode"] == "INVALID_EXPERIMENT_CONFIGURATION"
    assert _count_steps(experiment_id) == 0


def test_run_next_step_rejects_existing_running_step(client) -> None:
    create_response = client.post("/api/v1/experiments", json=_buy_and_hold_payload())
    experiment_id = create_response.json()["experiment"]["id"]
    _set_status(experiment_id, ExperimentStatus.RUNNING)

    engine = create_engine(_database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        session.add(
            ExecutionStepModel(
                experiment_id=experiment_id,
                scheduled_for=datetime(2024, 1, 2),
                started_at=datetime(2026, 1, 1, 12, 0, 0),
                completed_at=None,
                status=ExecutionStepStatus.RUNNING,
                trigger_type=TriggerType.MANUAL,
                sequence_number=1,
                error_message=None,
                created_at=datetime(2026, 1, 1, 12, 0, 0),
            )
        )
        session.commit()
    engine.dispose()

    response = client.post(f"/api/v1/experiments/{experiment_id}/run-next-step")

    assert response.status_code == 409
    assert response.json()["errorCode"] == "EXPERIMENT_STEP_ALREADY_RUNNING"


def test_run_next_step_missing_experiment_returns_404(client) -> None:
    response = client.post("/api/v1/experiments/9999/run-next-step")

    assert response.status_code == 404
    assert response.json()["errorCode"] == "EXPERIMENT_NOT_FOUND"
