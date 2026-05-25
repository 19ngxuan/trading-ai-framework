def test_options_endpoint_returns_documented_enums(client) -> None:
    response = client.get("/api/v1/options")
    assert response.status_code == 200

    body = response.json()
    assert body["assets"] == ["SPY"]
    assert "HISTORICAL_SIMULATION" in body["modes"]
    assert "PAPER_TRADING" in body["modes"]
    assert "AGENTIC_AI" in body["strategies"]
    assert "OPENING_RANGE_BREAKOUT" in body["strategies"]
    assert "CREATED" in body["experimentStatuses"]
    assert "INTRADAY_5_MIN" in body["tradingFrequencies"]
    assert "NONE" in body["feeModelTypes"]
    assert "SINGLE_AGENT" in body["agentModes"]
    assert "FILLED" in body["orderStatuses"]
