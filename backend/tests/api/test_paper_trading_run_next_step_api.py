from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.enums import ExecutionStepStatus, ExperimentStatus
from app.modules.execution.step_runner import StepRunResult
from app.persistence.database import get_database_url
from app.persistence.models import ExecutionStepModel, ExperimentModel, OrderModel


def _paper_trading_payload() -> dict:
    return {
        "name": "M9 Paper Trading",
        "mode": "PAPER_TRADING",
        "strategyType": "BUY_AND_HOLD",
        "assetSymbol": "SPY",
        "initialCapital": 10000,
        "startDate": "2026-01-01",
        "endDate": "2026-01-31",
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


def _count(model, experiment_id: int) -> int:
    engine = create_engine(_database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        count = int(
            session.scalar(
                select(func.count(model.id)).where(model.experiment_id == experiment_id)
            )
            or 0
        )
    engine.dispose()
    return count


def test_start_for_paper_trading_is_lifecycle_only(client) -> None:
    create_response = client.post("/api/v1/experiments", json=_paper_trading_payload())
    experiment_id = create_response.json()["experiment"]["id"]

    response = client.post(f"/api/v1/experiments/{experiment_id}/start")

    assert response.status_code == 202
    assert response.json()["status"] == "RUNNING"
    assert _count(ExecutionStepModel, experiment_id) == 0
    assert _count(OrderModel, experiment_id) == 0


def test_paper_trading_run_next_step_dispatches_to_paper_runner(
    client, monkeypatch
) -> None:
    create_response = client.post("/api/v1/experiments", json=_paper_trading_payload())
    experiment_id = create_response.json()["experiment"]["id"]
    _set_status(experiment_id, ExperimentStatus.RUNNING)
    seen: dict[str, int] = {}

    class FakePaperTradingStepRunner:
        def run_next_step(self, received_experiment_id: int) -> StepRunResult:
            seen["experimentId"] = received_experiment_id
            return StepRunResult(
                experiment_id=received_experiment_id,
                execution_step_id=42,
                status=ExecutionStepStatus.COMPLETED,
                message="Paper trading execution step completed.",
            )

    monkeypatch.setattr(
        "app.api.routes.experiments.PaperTradingStepRunner",
        FakePaperTradingStepRunner,
    )

    response = client.post(f"/api/v1/experiments/{experiment_id}/run-next-step")

    assert response.status_code == 202
    assert response.json() == {
        "experimentId": experiment_id,
        "executionStepId": 42,
        "status": "COMPLETED",
        "message": "Paper trading execution step completed.",
    }
    assert seen == {"experimentId": experiment_id}


def test_paper_trading_run_next_step_rejects_when_disabled(client) -> None:
    create_response = client.post("/api/v1/experiments", json=_paper_trading_payload())
    experiment_id = create_response.json()["experiment"]["id"]
    _set_status(experiment_id, ExperimentStatus.RUNNING)

    response = client.post(f"/api/v1/experiments/{experiment_id}/run-next-step")

    assert response.status_code == 409
    assert response.json()["errorCode"] == "INVALID_EXPERIMENT_CONFIGURATION"
    assert _count(ExecutionStepModel, experiment_id) == 0
