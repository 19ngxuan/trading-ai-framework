from datetime import datetime

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.enums import (
    ExecutionStepStatus,
    ExperimentStatus,
    SystemEventType,
    TriggerType,
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
            "strategyVersion": "buy-and-hold-v1",
            "movingAverageWindow": None,
            "positionSizingType": "ALL_IN",
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
        "strategyVersion": "moving-average-v1",
        "movingAverageWindow": 3,
        "positionSizingType": "ALL_IN",
        "agentMode": None,
        "modelName": None,
        "confidenceThreshold": None,
        "parametersJson": {"riskConfig": {"fallbackAction": "HOLD"}},
    }
    return payload


def _agentic_ai_payload() -> dict:
    payload = _buy_and_hold_payload()
    payload["name"] = "M10 Agentic AI"
    payload["strategyType"] = "AGENTIC_AI"
    payload["strategyConfig"] = {
        "strategyVersion": "agentic-ai-v1",
        "movingAverageWindow": None,
        "positionSizingType": "ALL_IN",
        "agentMode": "SINGLE_AGENT",
        "modelName": "deterministic-fake-agent",
        "confidenceThreshold": None,
        "parametersJson": {
            "riskConfig": {"fallbackAction": "HOLD"},
            "fakeAgent": {
                "output": {
                    "action": "HOLD",
                    "confidence": 0.8,
                    "rationale": "API deterministic hold.",
                }
            },
        },
    }
    return payload


def _agentic_ai_pipeline_payload() -> dict:
    payload = _agentic_ai_payload()
    payload["name"] = "M11 Agentic AI Pipeline"
    payload["strategyConfig"]["agentMode"] = "PIPELINE"
    payload["strategyConfig"]["modelName"] = "deterministic-fake-pipeline"
    payload["strategyConfig"]["parametersJson"] = {
        "riskConfig": {"fallbackAction": "HOLD"},
        "fakePipeline": {
            "marketAnalystOutput": {
                "marketBias": "BULLISH",
                "confidence": 0.8,
                "rationale": "Bullish context.",
            },
            "tradingDecisionOutput": {
                "action": "HOLD",
                "confidence": 0.8,
                "rationale": "Pipeline deterministic hold.",
            },
            "riskManagerOutput": {
                "verdict": "APPROVE",
                "confidence": 0.9,
                "rationale": "Approved.",
            },
        },
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


def test_run_next_step_executes_one_agentic_ai_bar(client) -> None:
    create_response = client.post("/api/v1/experiments", json=_agentic_ai_payload())
    experiment_id = create_response.json()["experiment"]["id"]
    _set_status(experiment_id, ExperimentStatus.RUNNING)

    response = client.post(f"/api/v1/experiments/{experiment_id}/run-next-step")

    assert response.status_code == 202
    body = response.json()
    assert body["experimentId"] == experiment_id
    assert body["executionStepId"] is not None
    assert body["status"] == "COMPLETED"
    assert _count_steps(experiment_id) == 1


def test_start_for_agentic_ai_is_lifecycle_only(client) -> None:
    create_response = client.post("/api/v1/experiments", json=_agentic_ai_payload())
    experiment_id = create_response.json()["experiment"]["id"]

    response = client.post(f"/api/v1/experiments/{experiment_id}/start")

    assert response.status_code == 202
    assert response.json()["status"] == "RUNNING"
    assert _count_steps(experiment_id) == 0


def test_start_for_agentic_ai_pipeline_is_lifecycle_only(client) -> None:
    create_response = client.post(
        "/api/v1/experiments", json=_agentic_ai_pipeline_payload()
    )
    experiment_id = create_response.json()["experiment"]["id"]

    response = client.post(f"/api/v1/experiments/{experiment_id}/start")

    assert response.status_code == 202
    assert response.json()["status"] == "RUNNING"
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
