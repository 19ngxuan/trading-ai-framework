# Trading Lab

Trading Lab is a web-based strategy and agentic-AI trading experimentation platform for SPY simulation and paper trading.

This repository currently contains the M0-M24 backend/frontend foundation:

- FastAPI backend skeleton
- React/Vite/TypeScript frontend skeleton
- PostgreSQL Docker Compose service
- Environment example files
- Backend health, experiment, and options API endpoints
- Deterministic Buy-and-Hold historical simulation for `BUY_AND_HOLD` + `HISTORICAL_SIMULATION`
- Deterministic Moving Average historical simulation for `MOVING_AVERAGE` + `HISTORICAL_SIMULATION`
- Opening Range Breakout historical simulation for `OPENING_RANGE_BREAKOUT` + `HISTORICAL_SIMULATION` + `INTRADAY_5_MIN`, using local CSV by default or Alpaca 5-minute bars when configured
- Metrics and portfolio snapshot APIs
- Frontend dashboard, experiment creation, and experiment detail views
- Frontend compare and events views
- Interactive portfolio, return, and comparison charts with zoom, pan, crosshair, and responsive sizing
- Manual run-next-step support for deterministic historical execution
- Optional backend scheduler infrastructure for scheduled historical steps
- Optional Alpaca market data adapter behind the backend market data module
- Optional Alpaca paper trading adapter for manual or scheduled `PAPER_TRADING` + `BUY_AND_HOLD` + `DAILY` SPY experiments, manual/scheduled `MOVING_AVERAGE` daily SPY paper experiments, scheduled `OPENING_RANGE_BREAKOUT` 5-minute SPY paper experiments, scheduled smoke-test diagnostics, and `AGENTIC_AI` single-agent daily SPY paper experiments when ScaDS.AI is explicitly enabled
- Deterministic single-agent and pipeline-agent `AGENTIC_AI` historical manual steps using fake providers only
- Optional ScaDS.AI single-agent provider for paper-trading `AGENTIC_AI`
- RiskCheck-controlled whole-share execution sizing
- Backend domain enums, SQLAlchemy models, Alembic migration setup, repository skeletons, and PostgreSQL-backed tests

The current implementation intentionally does not include real-money trading,
broker account/position reconciliation, historical scheduler-triggered Opening
Range Breakout execution, Opening Range Breakout manual `run-next-step`,
Agentic-AI pipeline paper trading, ORB/intraday agent paper trading, prompt
editing, tool calling, public execution-step or agent-log detail APIs, or
frontend trading action controls.

Trading Lab is not financial advice and is not a live trading system. Version 1 is for simulation and Alpaca paper trading only.

## Requirements

- Python 3.11+
- uv
- Node.js 20+
- npm
- Docker and Docker Compose

## Docker Setup

```bash
cp .env.example .env
docker compose up --build
```

For reset without DB loss:
```bash
docker compose down
docker compose up --build
```

If you want to fully reset DB:
```bash
docker compose down --v
docker compose up --build
cd backend
DATABASE_URL=postgresql://trading_lab:trading_lab_password@127.0.0.1:5433/trading_lab uv run alembic upgrade head
```

Services:

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/api/v1/health
- PostgreSQL from host: 127.0.0.1:5433
- PostgreSQL from Docker services: postgres:5432

Smoke check:

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "trading-lab-backend",
  "version": "0.1.0"
}
```

## Backend Local Development

```bash
cd backend
uv sync --extra dev
export DATABASE_URL=postgresql://trading_lab:trading_lab_password@127.0.0.1:5433/trading_lab
uv run uvicorn app.main:app --reload
uv run pytest
```

Scheduler settings are disabled by default:

```bash
SCHEDULER_ENABLED=false
SCHEDULER_INTERVAL_SECONDS=60
SCHEDULER_JOB_ID=historical_step_scheduler
PAPER_TRADING_SCHEDULER_ENABLED=false
PAPER_TRADING_SCHEDULER_INTERVAL_SECONDS=60
PAPER_TRADING_SCHEDULER_JOB_ID=paper_trading_scheduler
PAPER_TRADING_DAILY_EVALUATION_TIME=15:55
PAPER_TRADING_TEST_MODE_ENABLED=false
```

When enabled, the in-process historical scheduler advances each eligible running
historical Buy-and-Hold or Moving Average experiment by one step per tick.
Paper trading uses a separate disabled-by-default scheduler. When
`PAPER_TRADING_SCHEDULER_ENABLED=true` and Alpaca paper trading is enabled, the
paper scheduler evaluates eligible running daily `BUY_AND_HOLD`,
`MOVING_AVERAGE`, and `AGENTIC_AI` single-agent SPY paper experiments at or after
`PAPER_TRADING_DAILY_EVALUATION_TIME` in America/New_York. It also evaluates
scheduled `OPENING_RANGE_BREAKOUT` + `INTRADAY_5_MIN` + `SPY` paper experiments
on completed regular-session 5-minute bars. A separate broker-sync job continues polling submitted
paper orders until terminal broker status, including for paused or stopped
experiments. Scheduler-enabled mode assumes a single backend instance. In
multi-instance deployments, enable scheduler jobs on at most one backend
instance; M20 does not implement leader election.

Market data uses the deterministic local CSV fixture by default:

```bash
MARKET_DATA_PROVIDER=csv
ALPACA_API_KEY_ID=
ALPACA_API_SECRET_KEY=
ALPACA_DATA_BASE_URL=https://data.alpaca.markets
ALPACA_DATA_FEED=iex
ALPACA_DATA_ADJUSTMENT=all
ALPACA_REQUEST_TIMEOUT_SECONDS=10
ALPACA_PAPER_TRADING_ENABLED=false
ALPACA_TRADING_BASE_URL=https://paper-api.alpaca.markets
ALPACA_ORDER_TIMEOUT_SECONDS=10
SCADSAI_LLM_ENABLED=false
SCADSAI_API_KEY=
SCADSAI_BASE_URL=https://llm.scads.ai/v1
SCADSAI_REQUEST_TIMEOUT_SECONDS=30
SCADSAI_ALLOWED_MODELS=meta-llama/Llama-3.3-70B-Instruct
SCADSAI_DEFAULT_MODEL=meta-llama/Llama-3.3-70B-Instruct
```

Set `MARKET_DATA_PROVIDER=alpaca` only when Alpaca credentials are configured.
CSV remains the default for deterministic local development and tests. Tests use
CSV fixtures or mocked HTTP transports and do not require real Alpaca network
access. When Alpaca is selected, empty or missing market data is fatal; the
system does not forward-fill or interpolate bars. Opening Range Breakout uses
the same provider selection: local `spy_5min.csv` when `csv`, or Alpaca
historical `5Min` SPY bars when `alpaca`.

Paper trading is disabled by default and only accepts the Alpaca paper trading
base URL. It supports SPY Buy-and-Hold daily paper trading, SPY Moving Average
daily paper trading, scheduled SPY Opening Range Breakout 5-minute paper
trading, gated smoke-test diagnostics, and SPY Agentic-AI single-agent daily
paper trading when ScaDS.AI is enabled. Manual `run-next-step` remains supported
for Buy-and-Hold, Moving Average, and Agentic-AI paper debugging. Opening Range
Breakout paper trading is scheduled-only and skips before step creation if the
expected completed 5-minute bar is not available. Scheduled paper execution is available only when
`PAPER_TRADING_SCHEDULER_ENABLED=true`. Real-money Alpaca trading URLs are
rejected by configuration validation and by the broker adapter. M20 adds
order-status polling for submitted paper orders. Full broker
reconciliation, outbox processing, account sync, position sync, and automatic
order cancellation are not implemented.

M22 adds a disabled-by-default paper-trading smoke-test strategy for local
operations testing. When `PAPER_TRADING_TEST_MODE_ENABLED=true`, create options
may expose `PAPER_TRADING_SMOKE_TEST` + `TEST_1_MIN` for `PAPER_TRADING` + `SPY`
only. It runs from the paper scheduler during US regular market hours and
alternates fixed 1-share Alpaca paper BUY/SELL orders through the normal
TradingDecision -> RiskCheck -> Order/Trade path. Manual `run-next-step` is
rejected for this strategy. This is a diagnostics feature, not an investment
strategy.

M21 adds read-only paper trading operations visibility. Experiment detail pages
can show paper scheduler status, persisted orders, trades, and broker sync logs.
These views are audit/inspection surfaces only; they do not submit, cancel,
retry, or sync broker orders on demand.

Agentic AI historical execution remains deterministic. `AGENTIC_AI` historical
manual `run-next-step` supports `HISTORICAL_SIMULATION` + `DAILY` + `SPY` with
fake single-agent or pipeline providers configured through strategy parameters.
Paper-trading `AGENTIC_AI` supports only `SINGLE_AGENT` + `DAILY` + `SPY` and
uses the ScaDS.AI OpenAI-compatible API only when `SCADSAI_LLM_ENABLED=true`,
`SCADSAI_API_KEY` is configured, and the selected model is listed in
`SCADSAI_ALLOWED_MODELS`. Pipeline-agent paper trading, prompt editing, tool
calling, and direct agent access to broker, market data, scheduler, persistence,
or secrets remain out of scope.

Strategies and agents propose only `BUY`, `SELL`, or `HOLD`. The RiskCheck is
authoritative and determines the executable whole-share quantity from the
current portfolio state. BUY uses available cash, SELL liquidates the existing
long SPY position, and the system never opens short positions. If available cash
cannot buy one whole share, the final action becomes HOLD with an auditable
reason.

## Database Migrations

Start PostgreSQL first:

```bash
cp .env.example .env
docker compose up -d postgres
```

Apply migrations locally:

```bash
cd backend
DATABASE_URL=postgresql://trading_lab:trading_lab_password@127.0.0.1:5433/trading_lab uv run alembic upgrade head
```

Database smoke tests use `TEST_DATABASE_URL` when set, otherwise `DATABASE_URL`.
If neither URL is configured, database tests skip with an explicit reason. If a URL is configured but PostgreSQL is unreachable, database tests fail.

Run PostgreSQL-backed tests locally:

```bash
cd backend
DATABASE_URL=postgresql://trading_lab:trading_lab_password@127.0.0.1:5433/trading_lab uv run pytest
```

Docker-internal services use:

```bash
DATABASE_URL=postgresql://trading_lab:trading_lab_password@postgres:5432/trading_lab
```

## Frontend Local Development

```bash
cd frontend
npm install
npm run dev
npm run build
```

Implemented frontend routes:

- `/dashboard`
- `/experiments`
- `/experiments/new`
- `/experiments/:experimentId`
- `/compare`
- `/events`
- `/settings`

The frontend is presentation-only. It calls backend REST APIs and must not contain
trading, risk, broker, scheduler, market-data-provider, or agent decision logic.

## Environment Files

Use the committed `.env.example` files as templates:

- `.env.example`
- `backend/.env.example`
- `frontend/.env.example`

Do not commit real `.env` files or secrets.

## Architecture Notes

The backend is a FastAPI modular monolith. The frontend calls only backend REST APIs. PostgreSQL is the persistent database.

Version 1 is simulation and paper-trading only. Real-money trading,
live-trading endpoints, short selling, margin, options, and multi-user support
are out of scope. Agents must never access Alpaca or broker APIs directly; agent
output must be converted to a `TradingDecision` and pass through the system
RiskCheck before any execution path.

The core execution invariant is:

```text
Strategy / Agent
→ TradingDecision
→ RiskCheck
→ ExecutionStep
→ Order / Trade, when applicable
```

## Manual Smoke Checklist

After migrations and local services are running:

1. Create a `BUY_AND_HOLD` + `HISTORICAL_SIMULATION` + `DAILY` experiment and start it.
2. Create a `MOVING_AVERAGE` + `HISTORICAL_SIMULATION` + `DAILY` experiment and start it.
3. Create an `OPENING_RANGE_BREAKOUT` + `HISTORICAL_SIMULATION` + `INTRADAY_5_MIN` experiment and start it.
4. Create an `AGENTIC_AI` + `HISTORICAL_SIMULATION` + `DAILY` + `SPY` experiment with `agentMode=SINGLE_AGENT`, start it, then call `run-next-step`.
5. Create an `AGENTIC_AI` + `HISTORICAL_SIMULATION` + `DAILY` + `SPY` experiment with `agentMode=PIPELINE`, start it, then call `run-next-step`.
6. Verify metrics and portfolio snapshot charts on experiment detail.
7. Open `/compare`, select at least two experiments, and compare persisted metrics.
8. Open `/events` and verify lifecycle/system events are visible.
9. Validate paper-trading safety by confirming `ALPACA_PAPER_TRADING_ENABLED=false` rejects paper `run-next-step`, and that only the paper Alpaca base URL is accepted when enabled.
10. If ScaDS.AI is enabled, create an `AGENTIC_AI` + `PAPER_TRADING` + `SINGLE_AGENT` + `DAILY` + `SPY` experiment and verify that execution still persists `TradingDecision` then `RiskCheck` before any paper order.

## Known Limitations

- The CSV fixtures are deterministic and intentionally small; they are not full historical SPY coverage.
- `startDate` and `endDate` filter available bars; they do not guarantee data coverage.
- Opening Range Breakout uses local SPY 5-minute fixture data by default and Alpaca historical `5Min` bars when `MARKET_DATA_PROVIDER=alpaca`; it validates bars against the US equities calendar, supports early-close sessions, ignores weekends/holidays, and fails safely on missing expected session bars.
- Alpaca missing/empty bars are fatal; there is no forward-fill or interpolation.
- Scheduler mode assumes one backend instance; there is no leader election.
- Historical scheduler advances eligible historical Buy-and-Hold and Moving Average experiments only.
- Historical Opening Range Breakout runs through `/start` full-run only; manual `run-next-step` and historical scheduler-triggered ORB are deferred.
- Paper trading supports only the SPY workflows listed above; European ETF/Xetra production support is not implemented.
- Broker order-status polling exists for submitted paper orders. Full broker reconciliation, outbox processing, account sync, position sync, and automatic cancellation are deferred.
- Historical Agentic AI uses deterministic fake providers only. ScaDS.AI is used only for paper single-agent execution when explicitly enabled.
- Agentic AI pipeline paper trading, ORB/intraday agent trading, and real-money agent trading are not implemented.
- Compare UI loads selected experiment chart time series after the user runs a comparison.
- Public execution-step and agent-log list/detail APIs are deferred. Orders,
  trades, broker sync logs, and paper status are available as read-only
  experiment-scoped operations endpoints.
