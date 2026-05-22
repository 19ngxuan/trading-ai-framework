# API Specification

## 1. Purpose

This document defines the REST API contract for Trading Lab.

The API is used by the React frontend to create, control, inspect, and compare trading experiments.

The API does not expose direct access to Alpaca, the LLM provider, or the database. All external integrations are handled internally by the FastAPI backend.

---

## 2. API Principles

- All endpoints are versioned under `/api/v1`.
- All request and response bodies use JSON.
- The frontend communicates only with the Backend API.
- Experiment execution is asynchronous where appropriate.
- Long-running operations return `202 Accepted`.
- Lists are paginated with `limit` and `offset`.
- Errors use a consistent response format.
- IDs follow the current database schema and are represented as integer IDs.

---

## 3. Base URL

```http
/api/v1
```

Example:

```http
GET /api/v1/experiments
```

---

## 4. ID Format

The current database schema uses auto-incrementing `bigint` primary keys.

Therefore API examples use integer IDs:

```http
GET /api/v1/experiments/1
GET /api/v1/execution-steps/10
```

If the persistence model is changed to UUIDs later, this API contract must be updated together with the database schema.

---

## 5. Common Response Patterns

## 5.1 Pagination

Paginated endpoints use:

```http
?limit=50&offset=0
```

Paginated response format:

```json
{
  "items": [],
  "limit": 50,
  "offset": 0,
  "total": 0
}
```

Default values:

- `limit`: 50
- `offset`: 0

---

## 5.2 Error Response Format

All application errors should use this structure:

```json
{
  "errorCode": "INVALID_EXPERIMENT_STATUS",
  "message": "Experiment cannot be started because it is already running.",
  "details": {
    "experimentId": 1,
    "currentStatus": "RUNNING"
  }
}
```

Common error codes:

- `VALIDATION_ERROR`
- `EXPERIMENT_NOT_FOUND`
- `EXECUTION_STEP_NOT_FOUND`
- `INVALID_EXPERIMENT_STATUS`
- `MARKET_DATA_UNAVAILABLE`
- `BROKER_CONNECTION_FAILED`
- `BROKER_STATE_MISMATCH`
- `ORDER_REJECTED`
- `LLM_OUTPUT_INVALID`
- `RISK_LIMIT_TRIGGERED`
- `INTERNAL_ERROR`

---

## 5.3 HTTP Status Codes

| Status | Meaning |
|---|---|
| `200 OK` | Request succeeded. |
| `201 Created` | Resource was created. |
| `202 Accepted` | Asynchronous operation was accepted. |
| `400 Bad Request` | Invalid request. |
| `404 Not Found` | Resource does not exist. |
| `409 Conflict` | Invalid state transition or state conflict. |
| `422 Unprocessable Entity` | Validation failed. |
| `500 Internal Server Error` | Unexpected server error. |

---

## 6. Experiments API

## 6.1 Create Experiment

```http
POST /api/v1/experiments
```

Creates a new experiment in status `CREATED` and initializes its portfolio.

### Request

```json
{
  "name": "SPY 200MA Backtest",
  "mode": "HISTORICAL_SIMULATION",
  "strategyType": "MOVING_AVERAGE",
  "assetSymbol": "SPY",
  "initialCapital": 10000.0,
  "startDate": "2020-01-01",
  "endDate": "2024-12-31",
  "tradingFrequency": "DAILY",
  "feeModelType": "NONE",
  "feeValue": 0,
  "strategyConfig": {
    "strategyVersion": "moving-average-v1",
    "movingAverageWindow": 200,
    "positionSizingType": "ALL_IN",
    "agentMode": null,
    "modelName": null,
    "confidenceThreshold": null,
    "parametersJson": {
      "tradeOnCrossOnly": false,
      "useAdjustedClose": true
    }
  }
}
```

### Response `201 Created`

```json
{
  "experiment": {
    "id": 1,
    "name": "SPY 200MA Backtest",
    "mode": "HISTORICAL_SIMULATION",
    "strategyType": "MOVING_AVERAGE",
    "assetSymbol": "SPY",
    "status": "CREATED",
    "initialCapital": 10000.0,
    "startDate": "2020-01-01",
    "endDate": "2024-12-31",
    "tradingFrequency": "DAILY",
    "feeModelType": "NONE",
    "feeValue": 0,
    "createdAt": "2026-05-21T10:00:00Z",
    "updatedAt": "2026-05-21T10:00:00Z"
  },
  "portfolio": {
    "id": 1,
    "experimentId": 1,
    "cash": 10000.0,
    "positionSymbol": "SPY",
    "positionQuantity": 0,
    "currentPrice": null,
    "currentPositionValue": 0,
    "currentPortfolioValue": 10000.0,
    "updatedAt": "2026-05-21T10:00:00Z"
  }
}
```

---

## 6.2 List Experiments

```http
GET /api/v1/experiments
```

Returns a compact dashboard-oriented experiment list.

### Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `status` | string | Optional experiment status filter. |
| `strategyType` | string | Optional strategy type filter. |
| `mode` | string | Optional experiment mode filter. |
| `limit` | integer | Page size. |
| `offset` | integer | Page offset. |

### Example

```http
GET /api/v1/experiments?status=RUNNING&limit=20&offset=0
```

### Response `200 OK`

```json
{
  "items": [
    {
      "id": 1,
      "name": "SPY 200MA Backtest",
      "mode": "HISTORICAL_SIMULATION",
      "strategyType": "MOVING_AVERAGE",
      "assetSymbol": "SPY",
      "status": "RUNNING",
      "currentPortfolioValue": 10420.55,
      "totalReturn": 0.042,
      "profitLoss": 420.55,
      "numberOfTrades": 6,
      "maxDrawdown": -0.081,
      "lastTrade": {
        "side": "BUY",
        "quantity": 21,
        "price": 478.2,
        "timestamp": "2024-03-01T00:00:00Z"
      },
      "latestAgentDecisions": []
    }
  ],
  "limit": 20,
  "offset": 0,
  "total": 1
}
```

---

## 6.3 Get Experiment Detail

```http
GET /api/v1/experiments/{experiment_id}
```

Returns the complete high-level experiment detail.

### Response `200 OK`

```json
{
  "experiment": {
    "id": 1,
    "name": "SPY 200MA Backtest",
    "mode": "HISTORICAL_SIMULATION",
    "strategyType": "MOVING_AVERAGE",
    "assetSymbol": "SPY",
    "status": "COMPLETED",
    "initialCapital": 10000.0,
    "startDate": "2020-01-01",
    "endDate": "2024-12-31",
    "tradingFrequency": "DAILY",
    "feeModelType": "NONE",
    "feeValue": 0
  },
  "strategyConfig": {
    "id": 1,
    "experimentId": 1,
    "strategyType": "MOVING_AVERAGE",
    "strategyVersion": "moving-average-v1",
    "movingAverageWindow": 200,
    "positionSizingType": "ALL_IN",
    "agentMode": null,
    "modelName": null,
    "confidenceThreshold": null,
    "parametersJson": {
      "tradeOnCrossOnly": false,
      "useAdjustedClose": true
    }
  },
  "portfolio": {
    "id": 1,
    "experimentId": 1,
    "cash": 0,
    "positionSymbol": "SPY",
    "positionQuantity": 21,
    "currentPrice": 496.21,
    "currentPositionValue": 10420.41,
    "currentPortfolioValue": 10420.41
  },
  "latestMetrics": {
    "totalReturn": 0.042,
    "profitLoss": 420.41,
    "numberOfTrades": 6,
    "maxDrawdown": -0.081,
    "buyAndHoldReturn": 0.215,
    "differenceToBuyAndHold": -0.173
  },
  "latestAgentDecisions": []
}
```

---

## 6.4 Start Experiment

```http
POST /api/v1/experiments/{experiment_id}/start
```

Starts an experiment asynchronously.

### Response `202 Accepted`

```json
{
  "experimentId": 1,
  "status": "RUNNING",
  "message": "Experiment start accepted."
}
```

---

## 6.5 Pause Experiment

```http
POST /api/v1/experiments/{experiment_id}/pause
```

### Response `200 OK`

```json
{
  "experimentId": 1,
  "status": "PAUSED"
}
```

---

## 6.6 Resume Experiment

```http
POST /api/v1/experiments/{experiment_id}/resume
```

### Response `202 Accepted`

```json
{
  "experimentId": 1,
  "status": "RUNNING",
  "message": "Experiment resumed."
}
```

---

## 6.7 Stop Experiment

```http
POST /api/v1/experiments/{experiment_id}/stop
```

### Response `200 OK`

```json
{
  "experimentId": 1,
  "status": "STOPPED"
}
```

---

## 6.8 Run Next Step

```http
POST /api/v1/experiments/{experiment_id}/run-next-step
```

Triggers one manual execution step. This can be used for debugging historical, live-like, or paper-trading experiments.

### Request

```json
{
  "triggerReason": "Manual debug execution"
}
```

### Response `202 Accepted`

```json
{
  "experimentId": 1,
  "executionStepId": 100,
  "status": "RUNNING",
  "message": "Manual execution step accepted."
}
```

---

## 7. Execution Step API

## 7.1 List Execution Steps

```http
GET /api/v1/experiments/{experiment_id}/execution-steps
```

### Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `status` | string | Optional execution step status. |
| `triggerType` | string | Optional trigger type. |
| `limit` | integer | Page size. |
| `offset` | integer | Page offset. |

### Response `200 OK`

```json
{
  "items": [
    {
      "id": 100,
      "experimentId": 1,
      "scheduledFor": "2024-03-01T00:00:00Z",
      "startedAt": "2026-05-21T10:01:00Z",
      "completedAt": "2026-05-21T10:01:01Z",
      "status": "COMPLETED",
      "triggerType": "HISTORICAL",
      "sequenceNumber": 324,
      "errorMessage": null
    }
  ],
  "limit": 50,
  "offset": 0,
  "total": 1
}
```

---

## 7.2 Get Execution Step Detail

```http
GET /api/v1/execution-steps/{execution_step_id}
```

### Response `200 OK`

```json
{
  "executionStep": {
    "id": 100,
    "experimentId": 1,
    "status": "COMPLETED",
    "triggerType": "HISTORICAL",
    "sequenceNumber": 324
  },
  "marketDataSnapshot": {
    "symbol": "SPY",
    "price": 478.2,
    "movingAverage": 456.9,
    "rsi": 61.2
  },
  "tradingDecision": {
    "action": "BUY",
    "sourceType": "STRATEGY",
    "sourceName": "MovingAverageStrategy",
    "confidence": 1.0,
    "reason": "SPY price is above the 200-day moving average."
  },
  "riskCheck": {
    "approved": true,
    "finalAction": "BUY",
    "finalQuantity": 21,
    "finalNotional": 10042.2
  },
  "order": {
    "side": "BUY",
    "quantity": 21,
    "status": "FILLED"
  },
  "trade": {
    "side": "BUY",
    "quantity": 21,
    "price": 478.2,
    "orderValue": 10042.2
  },
  "portfolioSnapshot": {
    "cash": 0,
    "positionQuantity": 21,
    "totalPortfolioValue": 10042.2
  },
  "metricSnapshot": {
    "totalReturn": 0.0042,
    "profitLoss": 42.2,
    "numberOfTrades": 1,
    "maxDrawdown": 0
  }
}
```

---

## 8. Trades, Orders, Metrics, Portfolio

## 8.1 List Trades

```http
GET /api/v1/experiments/{experiment_id}/trades
```

Optional filters:

```http
?side=BUY&limit=50&offset=0
```

---

## 8.2 List Orders

```http
GET /api/v1/experiments/{experiment_id}/orders
```

Optional filters:

```http
?status=FAILED&limit=50&offset=0
```

---

## 8.3 List Metric Snapshots

```http
GET /api/v1/experiments/{experiment_id}/metrics
```

Used for metric timelines and charts.

---

## 8.4 List Portfolio Snapshots

```http
GET /api/v1/experiments/{experiment_id}/portfolio-snapshots
```

Used for equity curves and portfolio-value charts.

---

## 9. Agent Logs API

## 9.1 List Agent Logs

```http
GET /api/v1/experiments/{experiment_id}/agent-logs
```

### Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `agentMode` | string | Optional: `SINGLE_AGENT` or `PIPELINE`. |
| `agentStepName` | string | Optional pipeline step filter. |
| `parsingStatus` | string | Optional parsing status filter. |
| `limit` | integer | Page size. |
| `offset` | integer | Page offset. |

### Response `200 OK`

```json
{
  "items": [
    {
      "id": 1,
      "executionStepId": 100,
      "experimentId": 1,
      "tradingDecisionId": 200,
      "agentMode": "PIPELINE",
      "agentStepName": "MARKET_ANALYST",
      "agentName": "market-analyst-v1",
      "promptVersion": "market-analyst-prompt-v1",
      "modelName": "gpt-4.1",
      "modelVersion": "2026-xx",
      "inputJson": {
        "symbol": "SPY",
        "price": 478.2,
        "movingAverage": 456.9,
        "rsi": 61.2
      },
      "promptText": "...",
      "rawOutputText": "...",
      "parsedOutputJson": {
        "trendAssessment": "bullish",
        "riskNotes": "RSI not overbought"
      },
      "parsingStatus": "SUCCESS",
      "repairPromptText": null,
      "repairRawOutputText": null,
      "createdAt": "2026-05-21T10:01:00Z"
    }
  ],
  "limit": 50,
  "offset": 0,
  "total": 1
}
```

---

## 10. Events API

## 10.1 List System Events

```http
GET /api/v1/experiments/{experiment_id}/events
```

### Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `level` | string | Optional: `INFO`, `WARNING`, `ERROR`. |
| `eventType` | string | Optional system event type. |
| `limit` | integer | Page size. |
| `offset` | integer | Page offset. |

---

## 11. Broker Sync Logs API

```http
GET /api/v1/experiments/{experiment_id}/broker-sync-logs
```

Optional filters:

```http
?syncStatus=MISMATCH&limit=50&offset=0
```

---

## 12. Comparison API

## 12.1 Compare Experiments

```http
POST /api/v1/experiments/compare
```

### Request

```json
{
  "experimentIds": [1, 2, 3],
  "benchmarkExperimentId": 1
}
```

### Response `200 OK`

```json
{
  "benchmarkExperimentId": 1,
  "items": [
    {
      "experimentId": 2,
      "name": "SPY 200MA Backtest",
      "strategyType": "MOVING_AVERAGE",
      "totalReturn": 0.042,
      "profitLoss": 420.41,
      "numberOfTrades": 6,
      "maxDrawdown": -0.081,
      "benchmarkReturn": 0.215,
      "differenceToBenchmark": -0.173
    }
  ]
}
```

---

## 13. Options API

```http
GET /api/v1/options
```

Returns frontend-selectable enum values and supported options.

### Response `200 OK`

```json
{
  "assets": ["SPY"],
  "modes": ["HISTORICAL_SIMULATION", "LIVE_SIMULATION", "PAPER_TRADING"],
  "strategies": ["BUY_AND_HOLD", "MOVING_AVERAGE", "AGENTIC_AI"],
  "experimentStatuses": ["CREATED", "RUNNING", "PAUSED", "STOPPED", "COMPLETED", "FAILED"],
  "tradingFrequencies": ["DAILY", "WEEKLY", "MONTHLY"],
  "feeModelTypes": ["NONE", "FIXED", "PERCENTAGE"],
  "agentModes": ["SINGLE_AGENT", "PIPELINE"],
  "orderStatuses": ["CREATED", "SUBMITTED", "FILLED", "REJECTED", "FAILED", "CANCELLED"]
}
```

---

## 14. API Rules

1. The API must not expose direct Alpaca access to the frontend.
2. The API must not expose direct LLM provider access to the frontend.
3. The API must not expose direct database access.
4. Experiment start and manual execution endpoints should be asynchronous.
5. All execution must follow the backend pipeline:

```text
ExecutionStep
→ MarketDataSnapshot
→ TradingDecision
→ RiskCheck
→ Order/Trade
→ PortfolioSnapshot
→ MetricSnapshot
→ Logs
```

6. No endpoint may bypass the Risk Engine.
7. No endpoint may enable real-money trading in Version 1.
8. List endpoints should be paginated.
9. Error responses should use the common error format.
10. API changes must be reflected in `openapi.yaml`.

---

## 15. Related Documents

- `../01_architecture/system-overview.md`
- `../01_architecture/c4-container.md`
- `../01_architecture/c4-component.md`
- `../02_domain/entities.md`
- `../02_domain/workflows.md`
- `../02_domain/business-rules.md`
- `../04_database/schema.dbml`
- `../06_backend/service-contracts.md`
