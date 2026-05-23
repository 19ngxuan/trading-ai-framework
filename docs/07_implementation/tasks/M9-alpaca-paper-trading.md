# M9: Alpaca Paper Trading

## Goal

Add Alpaca Paper Trading behind the Broker Module for the narrow M9 paper execution path.

M9 is a safety-scoped paper-trading milestone. It does not add real-money trading, broker reconciliation, scheduled paper trading, or agent-driven broker access.

---

## Implemented Scope

- Backend-only Alpaca paper trading adapter.
- Broker adapter abstraction under `backend/app/modules/broker/`.
- Paper order submission through Alpaca paper endpoint only.
- Manual `POST /api/v1/experiments/{experiment_id}/run-next-step` dispatch for paper trading.
- Supported paper-trading experiment shape only:
  - `mode = PAPER_TRADING`
  - `strategy_type = BUY_AND_HOLD`
  - `trading_frequency = DAILY`
  - `asset_symbol = SPY`
  - `experiment.status = RUNNING`
- `/start` for `PAPER_TRADING` remains lifecycle-only and must never submit broker orders.
- Order submission occurs only after:
  - `ExecutionStep` is created
  - `TradingDecision` is persisted
  - `RiskCheck` is persisted
  - `RiskCheck.approved` is true
  - final action is `BUY` or `SELL`
  - final quantity is greater than zero
- `HOLD` and rejected risk decisions never call the broker.
- Filled and partially filled orders create local `Trade` rows only for filled quantity.
- Submitted but unfilled orders create local `Order` rows only and do not update the local portfolio.
- Broker rejected orders fail the step and experiment using `EXPERIMENT_FAILED` with `details_json.errorCode = ORDER_REJECTED`.
- Broker provider/network errors fail the step and experiment using `EXPERIMENT_FAILED` with `details_json.errorCode = BROKER_PROVIDER_ERROR`.

---

## Out Of Scope For M9

- No real-money trading.
- No live Alpaca trading endpoint.
- No scheduler-triggered paper trading.
- No Moving Average paper trading.
- No broker account reconciliation workflow.
- No broker position reconciliation workflow.
- No mismatch pause policy.
- No `BrokerSyncLog` workflow.
- No order polling or broker sync scheduler.
- No outbox.
- No frontend feature expansion.
- No LLM/agent logic.
- No direct broker access from strategies or agents.
- No schema migration, new tables, new columns, or new `SystemEventType` values.

---

## Configuration

Paper trading is disabled by default:

```text
ALPACA_PAPER_TRADING_ENABLED=false
ALPACA_TRADING_BASE_URL=https://paper-api.alpaca.markets
ALPACA_ORDER_TIMEOUT_SECONDS=10
```

`ALPACA_API_KEY_ID` and `ALPACA_API_SECRET_KEY` are required only when paper trading is enabled.

Both settings validation and the Alpaca paper adapter reject any trading base URL other than:

```text
https://paper-api.alpaca.markets
```

---

## Safety Rules

- Paper orders must go through the Broker Module.
- Strategies, agents, API routes, scheduler code, and frontend code must not call Alpaca broker APIs directly.
- The Risk Engine remains mandatory before execution.
- SELL may only close an existing long SPY position and must never open a short position.
- Only market orders are supported in M9.
- Tests must use fakes or `httpx.MockTransport`; real Alpaca network calls are not allowed in tests.

---

## Relevant Docs

- `docs/01_architecture/02_adr/ADR-005-risk-engine-before-execution.md`
- `docs/01_architecture/02_adr/ADR-007-alpaca-behind-adapters.md`
- `docs/01_architecture/02_adr/ADR-009-paper-trading-only.md`
- `docs/02_domain/03_business-rules.md`
- `docs/05_backend/service-contracts.md`

---

## Acceptance Criteria

- Manual paper `run-next-step` can submit a paper BUY order for a supported running experiment.
- `/start` for paper trading is lifecycle-only.
- Live Alpaca trading URLs are rejected.
- Broker submission cannot occur before persisted RiskCheck.
- HOLD/rejected risk decisions do not call the broker.
- Rejected broker orders and broker provider errors fail safely with `EXPERIMENT_FAILED`.
- Scheduler does not run paper trading.
- Existing historical simulations remain deterministic and CSV-backed by default.

---

## Test Requirements

- Broker adapter tests with mocked HTTP.
- Broker URL safety tests for live/non-HTTPS/arbitrary URLs.
- Paper step runner tests for filled, submitted, partial fill, rejected, provider error, HOLD, and unsupported configuration.
- API tests for `/start` lifecycle-only and `/run-next-step` paper dispatch.
- Scheduler tests proving paper trading is not selected.
- Full PostgreSQL-backed backend suite.

---

## Architecture Rules

- Do not bypass documented module boundaries.
- Keep the Strategy / Agent -> TradingDecision -> RiskCheck -> Execution pipeline intact.
- Do not introduce real-money trading.
- Update documentation if contracts, schemas, or behavior change.
