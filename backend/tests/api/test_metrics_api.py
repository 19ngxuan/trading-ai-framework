from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.enums import ExperimentStatus
from app.persistence.database import get_database_url
from app.persistence.models import ExperimentModel


def _buy_and_hold_payload() -> dict:
    return {
        "name": "M5 Buy and Hold",
        "mode": "HISTORICAL_SIMULATION",
        "strategyType": "BUY_AND_HOLD",
        "assetSymbol": "SPY",
        "initialCapital": 10000.0,
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


def _database_url() -> str:
    settings = get_settings()
    database_url = settings.test_database_url or settings.database_url
    assert database_url is not None
    return get_database_url(database_url)


def test_snapshot_endpoints_return_empty_items_before_simulation(client) -> None:
    create_response = client.post("/api/v1/experiments", json=_buy_and_hold_payload())
    experiment_id = create_response.json()["experiment"]["id"]

    metrics_response = client.get(f"/api/v1/experiments/{experiment_id}/metrics")
    portfolio_response = client.get(
        f"/api/v1/experiments/{experiment_id}/portfolio-snapshots"
    )

    assert metrics_response.status_code == 200
    assert metrics_response.json() == {"items": [], "limit": 50, "offset": 0, "total": 0}
    assert portfolio_response.status_code == 200
    assert portfolio_response.json() == {
        "items": [],
        "limit": 50,
        "offset": 0,
        "total": 0,
    }


def test_metrics_endpoint_returns_ascending_paginated_time_series(client) -> None:
    create_response = client.post("/api/v1/experiments", json=_buy_and_hold_payload())
    experiment_id = create_response.json()["experiment"]["id"]
    client.post(f"/api/v1/experiments/{experiment_id}/start")

    response = client.get(f"/api/v1/experiments/{experiment_id}/metrics?limit=2&offset=1")

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert body["total"] == 4
    assert [item["timestamp"] for item in body["items"]] == [
        "2024-01-03T00:00:00",
        "2024-01-04T00:00:00",
    ]
    assert body["items"][0]["numberOfTrades"] == 1
    assert body["items"][1]["totalReturn"] == 0.0042


def test_portfolio_snapshot_endpoint_returns_ascending_paginated_time_series(
    client,
) -> None:
    create_response = client.post("/api/v1/experiments", json=_buy_and_hold_payload())
    experiment_id = create_response.json()["experiment"]["id"]
    client.post(f"/api/v1/experiments/{experiment_id}/start")

    response = client.get(
        f"/api/v1/experiments/{experiment_id}/portfolio-snapshots?limit=2&offset=2"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 2
    assert body["offset"] == 2
    assert body["total"] == 4
    assert [item["timestamp"] for item in body["items"]] == [
        "2024-01-04T00:00:00",
        "2024-01-05T00:00:00",
    ]
    assert body["items"][0]["totalPortfolioValue"] == 10042.0
    assert body["items"][1]["currentPrice"] == 474.0


def test_snapshot_endpoints_accept_large_chart_limit(client) -> None:
    create_response = client.post("/api/v1/experiments", json=_buy_and_hold_payload())
    experiment_id = create_response.json()["experiment"]["id"]
    client.post(f"/api/v1/experiments/{experiment_id}/start")

    metrics_response = client.get(
        f"/api/v1/experiments/{experiment_id}/metrics?limit=10000&offset=0"
    )
    portfolio_response = client.get(
        f"/api/v1/experiments/{experiment_id}/portfolio-snapshots?limit=10000&offset=0"
    )

    assert metrics_response.status_code == 200
    assert metrics_response.json()["limit"] == 10000
    assert len(metrics_response.json()["items"]) == 4
    assert portfolio_response.status_code == 200
    assert portfolio_response.json()["limit"] == 10000
    assert len(portfolio_response.json()["items"]) == 4


def test_snapshot_endpoints_reject_limits_above_chart_max(client) -> None:
    create_response = client.post("/api/v1/experiments", json=_buy_and_hold_payload())
    experiment_id = create_response.json()["experiment"]["id"]

    metrics_response = client.get(
        f"/api/v1/experiments/{experiment_id}/metrics?limit=10001&offset=0"
    )
    portfolio_response = client.get(
        f"/api/v1/experiments/{experiment_id}/portfolio-snapshots?limit=10001&offset=0"
    )

    assert metrics_response.status_code == 422
    assert metrics_response.json()["errorCode"] == "VALIDATION_ERROR"
    assert portfolio_response.status_code == 422
    assert portfolio_response.json()["errorCode"] == "VALIDATION_ERROR"


def test_snapshot_endpoints_return_404_for_missing_experiment(client) -> None:
    metrics_response = client.get("/api/v1/experiments/9999/metrics")
    portfolio_response = client.get("/api/v1/experiments/9999/portfolio-snapshots")

    assert metrics_response.status_code == 404
    assert metrics_response.json()["errorCode"] == "EXPERIMENT_NOT_FOUND"
    assert portfolio_response.status_code == 404
    assert portfolio_response.json()["errorCode"] == "EXPERIMENT_NOT_FOUND"


def test_latest_metrics_are_returned_for_failed_experiment_with_snapshots(client) -> None:
    create_response = client.post("/api/v1/experiments", json=_buy_and_hold_payload())
    experiment_id = create_response.json()["experiment"]["id"]
    client.post(f"/api/v1/experiments/{experiment_id}/start")

    engine = create_engine(_database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        experiment = session.scalar(
            select(ExperimentModel).where(ExperimentModel.id == experiment_id)
        )
        assert experiment is not None
        experiment.status = ExperimentStatus.FAILED
        session.commit()
    engine.dispose()

    response = client.get(f"/api/v1/experiments/{experiment_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["experiment"]["status"] == "FAILED"
    assert body["latestMetrics"]["timestamp"] == "2024-01-05T00:00:00"
    assert body["latestMetrics"]["profitLoss"] == 63.0
