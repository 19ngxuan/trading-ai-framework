# Trading Lab

Trading Lab is a web-based strategy and agentic-AI trading experimentation platform for SPY simulation and paper trading.

This repository currently contains the M0/M1 foundation:

- FastAPI backend skeleton
- React/Vite/TypeScript frontend skeleton
- PostgreSQL Docker Compose service
- Environment example files
- Backend health endpoint
- Basic frontend app shell
- Backend domain enums, SQLAlchemy models, Alembic migration setup, repository skeletons, and database smoke tests

The current implementation intentionally does not include trading strategy execution, risk logic, broker integration, Alpaca integration, LLM integration, scheduler behavior, or public API endpoints beyond health.

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
- PostgreSQL: localhost:5432

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
DATABASE_URL=postgresql://trading_lab:trading_lab_password@localhost:5432/trading_lab uv run alembic upgrade head
```

Database smoke tests use `TEST_DATABASE_URL` when set, otherwise `DATABASE_URL`.
If neither URL is configured or PostgreSQL is unreachable, database tests skip with an explicit reason.

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
