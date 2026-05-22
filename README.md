# Trading Lab

Trading Lab is a web-based strategy and agentic-AI trading experimentation platform for SPY simulation and paper trading.

This repository currently contains the M0-M3 foundation:

- FastAPI backend skeleton
- React/Vite/TypeScript frontend skeleton
- PostgreSQL Docker Compose service
- Environment example files
- Backend health, experiment, and options API endpoints
- Deterministic Buy-and-Hold historical simulation for `BUY_AND_HOLD` + `HISTORICAL_SIMULATION`
- Basic frontend app shell
- Backend domain enums, SQLAlchemy models, Alembic migration setup, repository skeletons, and PostgreSQL-backed tests

The current implementation intentionally does not include Moving Average execution, Alpaca integration, external market data providers, broker integration, LLM/agent execution, scheduler behavior, or frontend trading UI.

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

## Environment Files

Use the committed `.env.example` files as templates:

- `.env.example`
- `backend/.env.example`
- `frontend/.env.example`

Do not commit real `.env` files or secrets.

## Architecture Notes

The backend is a FastAPI modular monolith. The frontend calls only backend REST APIs. PostgreSQL is the persistent database for later milestones.

Version 1 is simulation and paper-trading only. Real-money trading, live-trading endpoints, short selling, margin, options, and multi-user support are out of scope.
