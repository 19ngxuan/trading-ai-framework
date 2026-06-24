from datetime import datetime

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.domain.enums import (
    AgentMode,
    AgentStepName,
    ExecutionStepStatus,
    ExperimentStatus,
    ParsingStatus,
    SystemEventType,
    TriggerType,
)
from app.persistence.database import get_database_url
from app.persistence.models import (
    AgentDecisionLogModel,
    ExecutionStepModel,
    ExperimentModel,
    StrategyConfigModel,
    SystemEventLogModel,
)


def _create_request_payload() -> dict:
    return {
        "name": "M2 experiment",
        "mode": "HISTORICAL_SIMULATION",
        "strategyType": "BUY_AND_HOLD",
        "assetSymbol": "SPY",
        "initialCapital": 10000.0,
        "startDate": "2024-01-01",
        "endDate": "2024-12-31",
        "tradingFrequency": "DAILY",
        "feeModelType": "NONE",
        "feeValue": 0,
        "strategyConfig": {
            "movingAverageWindow": None,
            "agentMode": None,
            "modelName": None,
            "confidenceThreshold": None,
            "parametersJson": {
                "riskConfig": {
                    "fallbackAction": "HOLD",
                }
            },
        },
    }


def _create_buy_and_hold_payload() -> dict:
    payload = _create_request_payload()
    payload["name"] = "M3 Buy and Hold"
    payload["strategyType"] = "BUY_AND_HOLD"
    payload["startDate"] = "2024-01-02"
    payload["endDate"] = "2024-01-05"
    payload["strategyConfig"] = {
        "movingAverageWindow": None,
        "agentMode": None,
        "modelName": None,
        "confidenceThreshold": None,
        "parametersJson": {"riskConfig": {"fallbackAction": "HOLD"}},
    }
    return payload


def _create_paper_buy_and_hold_payload() -> dict:
    payload = _create_buy_and_hold_payload()
    payload["mode"] = "PAPER_TRADING"
    return payload


def _create_moving_average_payload() -> dict:
    payload = _create_request_payload()
    payload["name"] = "M4 Moving Average"
    payload["strategyType"] = "MOVING_AVERAGE"
    payload["startDate"] = "2024-01-02"
    payload["endDate"] = "2024-01-10"
    payload["tradingFrequency"] = "DAILY"
    payload["strategyConfig"] = {
        "movingAverageWindow": 3,
        "agentMode": None,
        "modelName": None,
        "confidenceThreshold": None,
        "parametersJson": {"riskConfig": {"fallbackAction": "HOLD"}},
    }
    return payload


def _create_opening_range_breakout_payload() -> dict:
    payload = _create_request_payload()
    payload["name"] = "M16 Opening Range Breakout"
    payload["strategyType"] = "OPENING_RANGE_BREAKOUT"
    payload["startDate"] = "2024-01-02"
    payload["endDate"] = "2024-01-02"
    payload["tradingFrequency"] = "INTRADAY_5_MIN"
    payload["strategyConfig"] = {
        "movingAverageWindow": None,
        "agentMode": None,
        "modelName": None,
        "confidenceThreshold": None,
        "parametersJson": {"riskConfig": {"fallbackAction": "HOLD"}},
    }
    return payload


def _create_paper_smoke_test_payload() -> dict:
    payload = _create_request_payload()
    payload["name"] = "M22 Paper Smoke Test"
    payload["mode"] = "PAPER_TRADING"
    payload["strategyType"] = "PAPER_TRADING_SMOKE_TEST"
    payload["tradingFrequency"] = "TEST_1_MIN"
    payload["strategyConfig"] = {
        "movingAverageWindow": None,
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


def test_create_experiment_creates_related_records_and_event(client) -> None:
    response = client.post("/api/v1/experiments", json=_create_request_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["experiment"]["status"] == "CREATED"
    assert body["portfolio"]["cash"] == 10000.0
    assert body["portfolio"]["positionSymbol"] is None
    assert body["portfolio"]["positionQuantity"] == 0.0
    assert body["portfolio"]["currentPositionValue"] == 0.0
    assert body["portfolio"]["currentPortfolioValue"] == 10000.0

    engine = create_engine(_database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        event_types = list(
            session.scalars(select(SystemEventLogModel.event_type).order_by(SystemEventLogModel.id))
        )
        assert event_types == [SystemEventType.EXPERIMENT_CREATED]
    engine.dispose()


def test_create_experiment_validation_error_is_normalized(client) -> None:
    payload = _create_request_payload()
    payload["assetSymbol"] = "QQQ"

    response = client.post("/api/v1/experiments", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["errorCode"] == "VALIDATION_ERROR"
    assert "message" in body
    assert "details" in body


def test_create_experiment_accepts_opening_range_breakout_intraday(client) -> None:
    response = client.post(
        "/api/v1/experiments",
        json=_create_opening_range_breakout_payload(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["experiment"]["strategyType"] == "OPENING_RANGE_BREAKOUT"
    assert body["experiment"]["tradingFrequency"] == "INTRADAY_5_MIN"


def test_create_experiment_accepts_moving_average_paper_trading(client) -> None:
    payload = _create_moving_average_payload()
    payload["mode"] = "PAPER_TRADING"

    response = client.post("/api/v1/experiments", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["experiment"]["mode"] == "PAPER_TRADING"
    assert body["experiment"]["strategyType"] == "MOVING_AVERAGE"
    assert body["experiment"]["tradingFrequency"] == "DAILY"


def test_create_experiment_accepts_orb_paper_trading(client) -> None:
    payload = _create_opening_range_breakout_payload()
    payload["mode"] = "PAPER_TRADING"

    response = client.post("/api/v1/experiments", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["experiment"]["mode"] == "PAPER_TRADING"
    assert body["experiment"]["strategyType"] == "OPENING_RANGE_BREAKOUT"
    assert body["experiment"]["tradingFrequency"] == "INTRADAY_5_MIN"


def test_create_experiment_rejects_agentic_ai_historical_simulation(client) -> None:
    payload = _create_request_payload()
    payload["mode"] = "HISTORICAL_SIMULATION"
    payload["strategyType"] = "AGENTIC_AI"

    response = client.post("/api/v1/experiments", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["errorCode"] == "VALIDATION_ERROR"
    assert body["details"]["mode"] == "HISTORICAL_SIMULATION"
    assert body["details"]["strategyType"] == "AGENTIC_AI"


def test_create_experiment_accepts_agentic_ai_paper_trading(client) -> None:
    payload = _create_request_payload()
    payload["mode"] = "PAPER_TRADING"
    payload["strategyType"] = "AGENTIC_AI"

    response = client.post("/api/v1/experiments", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["experiment"]["mode"] == "PAPER_TRADING"
    assert body["experiment"]["strategyType"] == "AGENTIC_AI"


def test_create_experiment_accepts_agentic_ai_pipeline_paper_trading(client) -> None:
    payload = _create_request_payload()
    payload["mode"] = "PAPER_TRADING"
    payload["strategyType"] = "AGENTIC_AI"
    payload["strategyConfig"]["agentMode"] = "PIPELINE"

    response = client.post("/api/v1/experiments", json=payload)

    assert response.status_code == 201
    assert response.json()["experiment"]["strategyType"] == "AGENTIC_AI"


def test_create_experiment_accepts_agentic_ai_hourly_paper_trading(client) -> None:
    payload = _create_request_payload()
    payload["mode"] = "PAPER_TRADING"
    payload["strategyType"] = "AGENTIC_AI"
    payload["tradingFrequency"] = "HOURLY"
    payload["strategyConfig"]["agentMode"] = "PIPELINE"

    response = client.post("/api/v1/experiments", json=payload)

    assert response.status_code == 201
    assert response.json()["experiment"]["tradingFrequency"] == "HOURLY"


def test_create_experiment_rejects_disallowed_scads_model(client) -> None:
    payload = _create_request_payload()
    payload["mode"] = "PAPER_TRADING"
    payload["strategyType"] = "AGENTIC_AI"
    payload["strategyConfig"]["agentMode"] = "SINGLE_AGENT"
    payload["strategyConfig"]["modelName"] = "not-allowed"

    response = client.post("/api/v1/experiments", json=payload)

    assert response.status_code == 422
    assert response.json()["errorCode"] == "VALIDATION_ERROR"


def test_create_experiment_rejects_unsupported_orb_configuration(client) -> None:
    payload = _create_opening_range_breakout_payload()
    payload["tradingFrequency"] = "DAILY"

    response = client.post("/api/v1/experiments", json=payload)

    assert response.status_code == 422
    assert response.json()["errorCode"] == "VALIDATION_ERROR"


def test_create_experiment_rejects_smoke_test_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("PAPER_TRADING_TEST_MODE_ENABLED", "false")
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/experiments", json=_create_paper_smoke_test_payload()
        )

    assert response.status_code == 422
    assert response.json()["errorCode"] == "VALIDATION_ERROR"
    get_settings.cache_clear()


def test_create_experiment_accepts_smoke_test_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("PAPER_TRADING_TEST_MODE_ENABLED", "true")
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/experiments",
            json=_create_paper_smoke_test_payload(),
        )

    assert response.status_code == 201
    body = response.json()
    assert body["experiment"]["mode"] == "PAPER_TRADING"
    assert body["experiment"]["strategyType"] == "PAPER_TRADING_SMOKE_TEST"
    assert body["experiment"]["tradingFrequency"] == "TEST_1_MIN"
    get_settings.cache_clear()


def test_create_experiment_rejects_unsupported_smoke_test_configuration(
    monkeypatch,
) -> None:
    monkeypatch.setenv("PAPER_TRADING_TEST_MODE_ENABLED", "true")
    get_settings.cache_clear()
    payload = _create_paper_smoke_test_payload()
    payload["tradingFrequency"] = "DAILY"

    with TestClient(create_app()) as client:
        response = client.post("/api/v1/experiments", json=payload)

    assert response.status_code == 422
    assert response.json()["errorCode"] == "VALIDATION_ERROR"
    get_settings.cache_clear()


def test_list_and_detail_experiments(client) -> None:
    create_response = client.post("/api/v1/experiments", json=_create_request_payload())
    experiment_id = create_response.json()["experiment"]["id"]

    list_response = client.get("/api/v1/experiments?limit=10&offset=0")
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["total"] == 1
    assert list_body["items"][0]["id"] == experiment_id
    assert list_body["items"][0]["latestAgentDecisions"] == []

    detail_response = client.get(f"/api/v1/experiments/{experiment_id}")
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["experiment"]["id"] == experiment_id
    assert detail_body["latestMetrics"] is None
    assert detail_body["latestAgentDecisions"] == []


def test_detail_includes_latest_agent_decision_logs(client) -> None:
    payload = _create_request_payload()
    payload["mode"] = "PAPER_TRADING"
    payload["strategyType"] = "AGENTIC_AI"
    payload["tradingFrequency"] = "DAILY"
    payload["strategyConfig"]["agentMode"] = "PIPELINE"
    create_response = client.post("/api/v1/experiments", json=payload)
    experiment_id = create_response.json()["experiment"]["id"]

    engine = create_engine(_database_url(), pool_pre_ping=True)
    now = datetime(2026, 1, 2, 15, 55, 0)
    with Session(engine) as session:
        config = session.scalar(
            select(StrategyConfigModel).where(
                StrategyConfigModel.experiment_id == experiment_id
            )
        )
        assert config is not None
        config.agent_mode = AgentMode.PIPELINE
        step = ExecutionStepModel(
            experiment_id=experiment_id,
            scheduled_for=None,
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
            AgentDecisionLogModel(
                execution_step_id=step.id,
                experiment_id=experiment_id,
                trading_decision_id=None,
                agent_mode=AgentMode.PIPELINE,
                agent_step_name=AgentStepName.FUNDAMENTAL_ANALYST,
                agent_name="MultiAgentDecisionGraph",
                prompt_version="multi-agent-graph-v1",
                model_name="meta-llama/Llama-3.3-70B-Instruct",
                model_version=None,
                input_json={"symbol": "SPY"},
                prompt_text="prompt",
                raw_output_text='{"signal":"BULLISH"}',
                parsed_output_json={"signal": "BULLISH", "summary": "Healthy."},
                parsing_status=ParsingStatus.SUCCESS,
                repair_prompt_text=None,
                repair_raw_output_text=None,
                created_at=now,
            )
        )
        session.commit()
    engine.dispose()

    detail_response = client.get(f"/api/v1/experiments/{experiment_id}")

    assert detail_response.status_code == 200
    logs = detail_response.json()["latestAgentDecisions"]
    assert len(logs) == 1
    assert logs[0]["agentStepName"] == "FUNDAMENTAL_ANALYST"
    assert logs[0]["parsedOutputJson"]["signal"] == "BULLISH"


def test_completed_experiment_list_and_detail_include_latest_metrics_and_trade(
    client,
) -> None:
    create_response = client.post("/api/v1/experiments", json=_create_buy_and_hold_payload())
    experiment_id = create_response.json()["experiment"]["id"]
    client.post(f"/api/v1/experiments/{experiment_id}/start")

    list_response = client.get("/api/v1/experiments?limit=10&offset=0")
    assert list_response.status_code == 200
    item = next(
        row for row in list_response.json()["items"] if row["id"] == experiment_id
    )
    assert item["totalReturn"] == 0.0063
    assert item["profitLoss"] == 63.0
    assert item["numberOfTrades"] == 1
    assert item["maxDrawdown"] == 0.0
    assert item["lastTrade"]["side"] == "BUY"
    assert item["lastTrade"]["quantity"] == 21.0
    assert item["lastTrade"]["price"] == 471.0
    assert item["latestAgentDecisions"] == []

    detail_response = client.get(f"/api/v1/experiments/{experiment_id}")
    assert detail_response.status_code == 200
    latest_metrics = detail_response.json()["latestMetrics"]
    assert latest_metrics["timestamp"] == "2024-01-05T00:00:00"
    assert latest_metrics["totalReturn"] == 0.0063
    assert latest_metrics["profitLoss"] == 63.0
    assert latest_metrics["numberOfTrades"] == 1
    assert latest_metrics["maxDrawdown"] == 0.0
    assert latest_metrics["buyAndHoldReturn"] == 0.0063
    assert latest_metrics["differenceToBuyAndHold"] == 0.0


def test_detail_not_found_returns_normalized_error(client) -> None:
    response = client.get("/api/v1/experiments/9999")
    assert response.status_code == 404
    body = response.json()
    assert body["errorCode"] == "EXPERIMENT_NOT_FOUND"


def test_lifecycle_transitions_and_events(client) -> None:
    create_response = client.post(
        "/api/v1/experiments",
        json=_create_paper_buy_and_hold_payload(),
    )
    experiment_id = create_response.json()["experiment"]["id"]

    start_response = client.post(f"/api/v1/experiments/{experiment_id}/start")
    assert start_response.status_code == 202
    assert start_response.json()["status"] == "RUNNING"

    pause_response = client.post(f"/api/v1/experiments/{experiment_id}/pause")
    assert pause_response.status_code == 200
    assert pause_response.json()["status"] == "PAUSED"

    resume_response = client.post(f"/api/v1/experiments/{experiment_id}/resume")
    assert resume_response.status_code == 202
    assert resume_response.json()["status"] == "RUNNING"

    stop_response = client.post(f"/api/v1/experiments/{experiment_id}/stop")
    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "STOPPED"

    engine = create_engine(_database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        statuses = list(session.scalars(select(ExperimentModel.status)))
        event_types = list(
            session.scalars(select(SystemEventLogModel.event_type).order_by(SystemEventLogModel.id))
        )
        assert statuses == [ExperimentStatus.STOPPED]
        assert event_types == [
            SystemEventType.EXPERIMENT_CREATED,
            SystemEventType.EXPERIMENT_STARTED,
            SystemEventType.EXPERIMENT_PAUSED,
            SystemEventType.EXPERIMENT_RESUMED,
            SystemEventType.EXPERIMENT_STOPPED,
        ]
    engine.dispose()


def test_invalid_transition_returns_409(client) -> None:
    create_response = client.post("/api/v1/experiments", json=_create_request_payload())
    experiment_id = create_response.json()["experiment"]["id"]

    start_response = client.post(f"/api/v1/experiments/{experiment_id}/start")
    assert start_response.status_code == 202

    invalid_start = client.post(f"/api/v1/experiments/{experiment_id}/start")
    assert invalid_start.status_code == 409
    body = invalid_start.json()
    assert body["errorCode"] == "INVALID_EXPERIMENT_STATUS"


def test_start_on_paused_is_rejected(client) -> None:
    create_response = client.post("/api/v1/experiments", json=_create_request_payload())
    experiment_id = create_response.json()["experiment"]["id"]
    client.post(f"/api/v1/experiments/{experiment_id}/start")
    client.post(f"/api/v1/experiments/{experiment_id}/pause")

    response = client.post(f"/api/v1/experiments/{experiment_id}/start")
    assert response.status_code == 409
    assert response.json()["errorCode"] == "INVALID_EXPERIMENT_STATUS"


def test_start_buy_and_hold_historical_runs_background_simulation(client) -> None:
    create_response = client.post("/api/v1/experiments", json=_create_buy_and_hold_payload())
    experiment_id = create_response.json()["experiment"]["id"]

    response = client.post(f"/api/v1/experiments/{experiment_id}/start")
    assert response.status_code == 202
    assert response.json()["status"] == "RUNNING"

    engine = create_engine(_database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        experiment = session.get(ExperimentModel, experiment_id)
        step_count = session.scalar(
            select(func.count(ExecutionStepModel.id)).where(
                ExecutionStepModel.experiment_id == experiment_id
            )
        )
        assert experiment is not None
        assert experiment.status is ExperimentStatus.COMPLETED
        assert step_count == 4
    engine.dispose()


def test_start_paper_experiment_remains_lifecycle_only(client) -> None:
    create_response = client.post(
        "/api/v1/experiments",
        json=_create_paper_buy_and_hold_payload(),
    )
    experiment_id = create_response.json()["experiment"]["id"]

    response = client.post(f"/api/v1/experiments/{experiment_id}/start")
    assert response.status_code == 202

    engine = create_engine(_database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        experiment = session.get(ExperimentModel, experiment_id)
        step_count = session.scalar(
            select(func.count(ExecutionStepModel.id)).where(
                ExecutionStepModel.experiment_id == experiment_id
            )
        )
        assert experiment is not None
        assert experiment.status is ExperimentStatus.RUNNING
        assert step_count == 0
    engine.dispose()


def test_start_moving_average_historical_runs_background_simulation(client) -> None:
    create_response = client.post(
        "/api/v1/experiments", json=_create_moving_average_payload()
    )
    experiment_id = create_response.json()["experiment"]["id"]

    response = client.post(f"/api/v1/experiments/{experiment_id}/start")
    assert response.status_code == 202
    assert response.json()["status"] == "RUNNING"

    engine = create_engine(_database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        experiment = session.get(ExperimentModel, experiment_id)
        step_count = session.scalar(
            select(func.count(ExecutionStepModel.id)).where(
                ExecutionStepModel.experiment_id == experiment_id
            )
        )
        assert experiment is not None
        assert experiment.status is ExperimentStatus.COMPLETED
        assert step_count == 7
    engine.dispose()


def test_start_opening_range_breakout_historical_runs_background_simulation(
    client,
) -> None:
    create_response = client.post(
        "/api/v1/experiments",
        json=_create_opening_range_breakout_payload(),
    )
    experiment_id = create_response.json()["experiment"]["id"]

    response = client.post(f"/api/v1/experiments/{experiment_id}/start")
    assert response.status_code == 202
    assert response.json()["status"] == "RUNNING"

    engine = create_engine(_database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        experiment = session.get(ExperimentModel, experiment_id)
        step_count = session.scalar(
            select(func.count(ExecutionStepModel.id)).where(
                ExecutionStepModel.experiment_id == experiment_id
            )
        )
        assert experiment is not None
        assert experiment.status is ExperimentStatus.COMPLETED
        assert step_count == 78
    engine.dispose()


def test_start_opening_range_breakout_paper_trading_is_lifecycle_only(
    client,
) -> None:
    payload = _create_opening_range_breakout_payload()
    payload["mode"] = "PAPER_TRADING"
    create_response = client.post("/api/v1/experiments", json=payload)
    experiment_id = create_response.json()["experiment"]["id"]

    response = client.post(f"/api/v1/experiments/{experiment_id}/start")
    assert response.status_code == 202
    assert response.json()["status"] == "RUNNING"

    engine = create_engine(_database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        experiment = session.get(ExperimentModel, experiment_id)
        step_count = session.scalar(
            select(func.count(ExecutionStepModel.id)).where(
                ExecutionStepModel.experiment_id == experiment_id
            )
        )
        assert experiment is not None
        assert experiment.status is ExperimentStatus.RUNNING
        assert step_count == 0
    engine.dispose()


def test_start_moving_average_non_daily_returns_409_without_artifacts(client) -> None:
    payload = _create_moving_average_payload()
    payload["tradingFrequency"] = "WEEKLY"
    create_response = client.post("/api/v1/experiments", json=payload)
    experiment_id = create_response.json()["experiment"]["id"]

    response = client.post(f"/api/v1/experiments/{experiment_id}/start")
    assert response.status_code == 409
    assert response.json()["errorCode"] == "INVALID_EXPERIMENT_CONFIGURATION"

    engine = create_engine(_database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        experiment = session.get(ExperimentModel, experiment_id)
        step_count = session.scalar(
            select(func.count(ExecutionStepModel.id)).where(
                ExecutionStepModel.experiment_id == experiment_id
            )
        )
        event_types = list(
            session.scalars(
                select(SystemEventLogModel.event_type).where(
                    SystemEventLogModel.experiment_id == experiment_id
                )
            )
        )
        assert experiment is not None
        assert experiment.status is ExperimentStatus.CREATED
        assert step_count == 0
        assert event_types == [SystemEventType.EXPERIMENT_CREATED]
    engine.dispose()
