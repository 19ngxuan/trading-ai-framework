# API Specification

## 1. Purpose

This document defines the REST API contract for Trading Lab.

The API is used by the React frontend to create, control, and inspect trading experiments.

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
POST /api/v1/experiments/1/run-next-step
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
    "movingAverageWindow": 200,
    "agentMode": null,
    "modelName": null,
    "confidenceThreshold": null,
    "parametersJson": {
      "tradeOnCrossOnly": false,
      "useAdjustedClose": true,
      "riskConfig": {
        "maxPositionSizePct": 1.0,
        "maxTradesPerDay": null,
        "maxTradesPerWeek": null,
        "maxDrawdownPct": null,
        "drawdownAction": "BLOCK_TRADES",
        "fallbackAction": "HOLD"
      }
    }
  }
}
```

Strategies and agents propose only `BUY`, `SELL`, or `HOLD`. The RiskCheck is
authoritative and determines the executable whole-share quantity from the
current portfolio state. BUY uses available cash, SELL liquidates the existing
long SPY position, and the system never opens short positions.

Opening Range Breakout creation is supported only for
`OPENING_RANGE_BREAKOUT` + `HISTORICAL_SIMULATION` + `INTRADAY_5_MIN` + `SPY`.
It uses local deterministic 5-minute SPY fixture data when
`MARKET_DATA_PROVIDER=csv`, and Alpaca historical 5-minute SPY bars when
`MARKET_DATA_PROVIDER=alpaca`. Intraday bars are validated against the US
equities trading calendar, including early-close sessions. Date ranges
containing only weekends or full market holidays complete with zero execution
steps.

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
    "positionSymbol": null,
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
    "movingAverageWindow": 200,
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
    "timestamp": "2024-03-01T00:00:00",
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

`start` is valid only for experiments in `CREATED`. A `PAUSED` experiment must use `/resume`; `start` on `PAUSED` returns `409 Conflict`.

Current `/start` full-run execution support:

- `BUY_AND_HOLD` + `HISTORICAL_SIMULATION` + `DAILY`
- `MOVING_AVERAGE` + `HISTORICAL_SIMULATION` + `DAILY`
- `OPENING_RANGE_BREAKOUT` + `HISTORICAL_SIMULATION` + `INTRADAY_5_MIN`

`/start` remains lifecycle-only for paper-trading and Agentic-AI experiments.

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

Triggers one manual execution step. In the current implementation this supports:

- `BUY_AND_HOLD` + `HISTORICAL_SIMULATION` + `DAILY`
- `MOVING_AVERAGE` + `HISTORICAL_SIMULATION` + `DAILY`
- `BUY_AND_HOLD` + `PAPER_TRADING` + `DAILY` for the supported paper-trading equity allowlist, only when Alpaca paper trading is explicitly enabled
- `MOVING_AVERAGE` + `PAPER_TRADING` + `DAILY` for the supported paper-trading equity allowlist, only when Alpaca paper trading is explicitly enabled
- `AGENTIC_AI` + `PAPER_TRADING` + (`SINGLE_AGENT` or `PIPELINE`) + (`DAILY` or `HOURLY`) for the supported paper-trading equity allowlist, only when Alpaca paper trading and ScaDS.AI are explicitly enabled

`PAPER_TRADING_SMOKE_TEST` and paper-trading Opening Range Breakout are
scheduled-only. Manual `run-next-step` is rejected for those experiments.

Opening Range Breakout is not supported by manual `run-next-step` in M16.
`/start` remains lifecycle-only for paper-trading experiments. It never submits
broker orders.

Manual run-next-step creates exactly one execution step and is intended for deterministic debugging. It uses the same execution pipeline as scheduled/background execution.

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
  "status": "COMPLETED",
  "message": "Manual execution step completed."
}
```

---

## 7. Metrics And Portfolio Snapshot APIs

## 7.1 List Metric Snapshots

```http
GET /api/v1/experiments/{experiment_id}/metrics
```

Used for metric timelines and charts.

Pagination follows the standard `limit`/`offset` shape. Chart clients may
request up to `limit=10000`; limits above `10000` return `422 VALIDATION_ERROR`.

---

## 7.2 List Portfolio Snapshots

```http
GET /api/v1/experiments/{experiment_id}/portfolio-snapshots
```

Used for equity curves and portfolio-value charts.

Pagination follows the standard `limit`/`offset` shape. Chart clients may
request up to `limit=10000`; limits above `10000` return `422 VALIDATION_ERROR`.

---

## 8. Comparison API

## 8.1 Compare Experiments

```http
POST /api/v1/experiments/compare
```

Compares selected experiments using existing persisted metrics and portfolio state.
The backend does not recalculate metrics in this endpoint.

### Request

```json
{
  "experimentIds": [1, 2],
  "benchmarkExperimentId": 1
}
```

`benchmarkExperimentId` is optional. If omitted, `benchmarkReturn` and
`differenceToBenchmark` are returned as `null`.

Validation rules:

- `experimentIds` must contain at least two unique IDs.
- duplicate IDs return `422 VALIDATION_ERROR`.
- `benchmarkExperimentId`, when provided, must be one of `experimentIds`.
- missing experiment IDs return `404 EXPERIMENT_NOT_FOUND`.

### Response `200 OK`

```json
{
  "benchmarkExperimentId": 1,
  "items": [
    {
      "experimentId": 1,
      "name": "SPY Buy and Hold",
      "mode": "HISTORICAL_SIMULATION",
      "strategyType": "BUY_AND_HOLD",
      "status": "COMPLETED",
      "assetSymbol": "SPY",
      "latestPortfolioValue": 10420.41,
      "totalReturn": 0.042,
      "profitLoss": 420.41,
      "numberOfTrades": 1,
      "maxDrawdown": 0,
      "benchmarkReturn": 0.042,
      "differenceToBenchmark": 0
    }
  ]
}
```

---

## 9. Events API

## 9.1 List System Events

```http
GET /api/v1/events
```

Returns persisted `SystemEventLog` records ordered by `timestamp DESC, id DESC`.

Query parameters:

| Parameter | Type | Description |
|---|---|---|
| `experimentId` | integer | Optional experiment filter. |
| `level` | string | Optional event level filter. |
| `eventType` | string | Optional system event type filter. |
| `limit` | integer | Page size. |
| `offset` | integer | Page offset. |

## 9.2 List Experiment System Events

```http
GET /api/v1/experiments/{experiment_id}/events
```

Returns persisted `SystemEventLog` records for one experiment. Missing experiments
return `404 EXPERIMENT_NOT_FOUND`.

### Response `200 OK`

```json
{
  "items": [
    {
      "id": 1,
      "experimentId": 1,
      "executionStepId": null,
      "timestamp": "2026-05-24T10:00:00",
      "level": "INFO",
      "eventType": "EXPERIMENT_CREATED",
      "message": "Experiment created.",
      "detailsJson": {
        "experimentId": 1
      },
      "createdAt": "2026-05-24T10:00:00"
    }
  ],
  "limit": 50,
  "offset": 0,
  "total": 1
}
```

M12 exposes `SystemEventLog` only. M21 adds read-only experiment-scoped
operations endpoints for persisted orders, trades, broker sync logs, and paper
trading status. These endpoints do not submit broker orders, poll Alpaca, or
change experiment state.

---

## 10. Paper Trading Operations APIs

The following endpoints are read-only audit endpoints:

```http
GET /api/v1/experiments/{experiment_id}/orders
GET /api/v1/experiments/{experiment_id}/trades
GET /api/v1/experiments/{experiment_id}/broker-sync-logs
GET /api/v1/experiments/{experiment_id}/paper-status
```

Orders, trades, and broker sync logs are paginated with `limit` and `offset` and
are sorted newest first. Missing experiments return the normalized
`EXPERIMENT_NOT_FOUND` response. The endpoints read persisted rows only and do
not call Alpaca.

`paper-status` explains the operational state of a paper trading experiment:

- whether the paper scheduler is enabled
- whether Alpaca paper trading is enabled
- whether the configuration is supported by the paper scheduler
- the configured daily evaluation time in `America/New_York`
- current or next eligible evaluation time if calculable
- whether the current due slot was already executed
- open submitted order count
- last broker sync timestamp
- the last execution step summary
- a reason code explaining why no new order may happen yet
- optional strategy-specific operational metadata, such as ORB due bar timestamps

Example reason codes include `PAPER_TRADING_SCHEDULER_DISABLED`,
`WAITING_FOR_DAILY_EVALUATION_TIME`, `OPEN_ORDER_PENDING_SYNC`,
`EXPERIMENT_NOT_RUNNING`, `PAPER_TRADING_TEST_MODE_DISABLED`,
`WAITING_FOR_REGULAR_MARKET_HOURS`, `CURRENT_TEST_SLOT_ALREADY_EXECUTED`, and
`READY_FOR_NEXT_SCHEDULED_EVALUATION`. ORB paper trading may also report
`WAITING_FOR_COMPLETED_INTRADAY_BAR` or
`CURRENT_INTRADAY_SLOT_ALREADY_EXECUTED`. Hourly Agentic-AI paper trading may
report `WAITING_FOR_COMPLETED_HOURLY_BAR` or
`CURRENT_HOURLY_SLOT_ALREADY_EXECUTED`.

Scheduled paper trading supports `BUY_AND_HOLD` + `DAILY`,
`MOVING_AVERAGE` + `DAILY`, and `AGENTIC_AI` with `SINGLE_AGENT` or
`PIPELINE` on `DAILY` or `HOURLY` cadence for the supported paper-trading
equity allowlist, plus
`OPENING_RANGE_BREAKOUT` + `INTRADAY_5_MIN` + `SPY`. Moving Average and
Agentic-AI manual `run-next-step` are supported for debugging. ORB paper
trading is scheduled-only and skips before step creation if the expected
completed 5-minute bar is unavailable.

M22 adds a disabled-by-default diagnostics strategy,
`PAPER_TRADING_SMOKE_TEST`. It is available in `/options` only when
`PAPER_TRADING_TEST_MODE_ENABLED=true`. It supports `PAPER_TRADING` +
`TEST_1_MIN` + `SPY` only, runs only from the paper scheduler during US regular
market hours, and creates alternating fixed 1-share paper BUY/SELL orders after
the normal RiskCheck path. It is not an investment strategy.

---

## 11. Not Yet Implemented As Public APIs

The current implementation persists execution steps, orders, trades, agent log
tables, and broker sync tables where applicable. Public list/detail endpoints
are still not implemented for:

- execution steps
- agent logs

These endpoints are intentionally deferred and must not be assumed available by frontend or API clients until implemented and documented.

Some OpenAPI component schemas may exist for deferred audit entities because the
database models already exist. A component schema alone does not imply a public
endpoint is implemented.

---

## 12. Options API

```http
GET /api/v1/options
```

Returns frontend-selectable enum values and supported options.

### Response `200 OK`

```json
{
  "assets": ["SPY", "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA"],
  "modes": ["HISTORICAL_SIMULATION", "PAPER_TRADING"],
  "strategies": ["BUY_AND_HOLD", "MOVING_AVERAGE", "AGENTIC_AI", "OPENING_RANGE_BREAKOUT"],
  "experimentStatuses": ["CREATED", "RUNNING", "PAUSED", "STOPPED", "COMPLETED", "FAILED"],
  "tradingFrequencies": ["DAILY", "WEEKLY", "MONTHLY", "HOURLY", "INTRADAY_5_MIN"],
  "feeModelTypes": ["NONE", "FIXED", "PERCENTAGE"],
  "agentModes": ["SINGLE_AGENT", "PIPELINE"],
  "orderStatuses": ["CREATED", "SUBMITTED", "FILLED", "REJECTED", "FAILED", "CANCELLED"],
  "scadsaiLlmEnabled": false,
  "scadsaiAllowedModels": [
    "alias-ha",
    "meta-llama/Llama-3.3-70B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
    "alias-reasoning",
    "alias-huge",
    "alias-huge-no-thinking",
    "Qwen/Qwen3-VL-8B-Instruct",
    "alias-vision",
    "openGPT-X/Teuken-7B-instruct-v0.6",
    "Qwen/Qwen3-Coder-30B-A3B-Instruct",
    "alias-code",
    "google/gemma-4-31B-it",
    "openai/gpt-oss-120b",
    "moonshotai/Kimi-K2.6",
    "MiniMaxAI/MiniMax-M2.7"
  ],
  "scadsaiDefaultModel": "meta-llama/Llama-3.3-70B-Instruct"
}
```

`PAPER_TRADING_SMOKE_TEST` and `TEST_1_MIN` are included only when
`PAPER_TRADING_TEST_MODE_ENABLED=true`.

Frontend create flows may still hide combinations that are technically listed in
`/options` but not supported for the current mode/strategy selection UX. The
backend remains authoritative for create-time and runtime validation.

---

## 12. API Rules

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

## 13. Related Documents

- `../01_architecture/system-overview.md`
- `../01_architecture/01_c4-model/c4-container.md`
- `../01_architecture/01_c4-model/c4-component.md`
- `../02_domain/01_entities.md`
- `../02_domain/02_workflows.md`
- `../02_domain/03_business-rules.md`
- `../03_database/schema.dbml`
- `../05_backend/service-contracts.md`
