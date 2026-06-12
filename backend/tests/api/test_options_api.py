from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def test_options_endpoint_returns_documented_enums(monkeypatch) -> None:
    monkeypatch.setenv("PAPER_TRADING_TEST_MODE_ENABLED", "false")
    monkeypatch.setenv("SCADSAI_LLM_ENABLED", "false")
    monkeypatch.setenv(
        "SCADSAI_ALLOWED_MODELS", "meta-llama/Llama-3.3-70B-Instruct"
    )
    monkeypatch.setenv(
        "SCADSAI_DEFAULT_MODEL", "meta-llama/Llama-3.3-70B-Instruct"
    )
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        response = client.get("/api/v1/options")
    assert response.status_code == 200

    body = response.json()
    assert body["assets"] == ["SPY"]
    assert "HISTORICAL_SIMULATION" in body["modes"]
    assert "PAPER_TRADING" in body["modes"]
    assert "AGENTIC_AI" in body["strategies"]
    assert "OPENING_RANGE_BREAKOUT" in body["strategies"]
    assert "PAPER_TRADING_SMOKE_TEST" not in body["strategies"]
    assert "CREATED" in body["experimentStatuses"]
    assert "INTRADAY_5_MIN" in body["tradingFrequencies"]
    assert "TEST_1_MIN" not in body["tradingFrequencies"]
    assert "NONE" in body["feeModelTypes"]
    assert "SINGLE_AGENT" in body["agentModes"]
    assert "FILLED" in body["orderStatuses"]
    assert body["scadsaiLlmEnabled"] is False
    assert body["scadsaiDefaultModel"] == "meta-llama/Llama-3.3-70B-Instruct"
    assert "meta-llama/Llama-3.3-70B-Instruct" in body["scadsaiAllowedModels"]
    get_settings.cache_clear()


def test_options_endpoint_includes_smoke_test_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("PAPER_TRADING_TEST_MODE_ENABLED", "true")
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        response = client.get("/api/v1/options")

    assert response.status_code == 200
    body = response.json()
    assert "PAPER_TRADING_SMOKE_TEST" in body["strategies"]
    assert "TEST_1_MIN" in body["tradingFrequencies"]
    get_settings.cache_clear()
