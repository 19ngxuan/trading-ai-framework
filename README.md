# Trading Lab

Trading Lab is a web-based strategy and agentic-AI trading experimentation platform for SPY simulation and paper trading.

This repository currently contains the M0 scaffold:

- FastAPI backend skeleton
- React/Vite/TypeScript frontend skeleton
- PostgreSQL Docker Compose service
- Environment example files
- Backend health endpoint
- Basic frontend app shell

M0 intentionally does not include trading logic, domain models, database schema, migrations, broker integration, Alpaca integration, LLM integration, or scheduler behavior.

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
