# M0: Repository and Setup

## Goal

Create the initial monorepo, FastAPI backend, React frontend, PostgreSQL service, and Docker Compose setup.

---

## Scope

- Create top-level repository structure
- Initialize backend FastAPI project
- Initialize frontend React/Vite/TypeScript project
- Add Docker Compose with PostgreSQL
- Add root README and .env.example
- Add health endpoint

---

## Out of Scope

- No trading logic
- No database schema beyond connectivity
- No Alpaca or LLM integration

---

## Relevant Docs

- docs/01_architecture/system-overview.md
- docs/01_architecture/decisions.md
- docs/07_implementation/01_coding-standards.md

---

## Acceptance Criteria

- docker compose up starts services
- GET /api/v1/health returns 200
- Frontend renders a basic app shell
- Secrets are not committed

---

## Test Requirements

- Basic backend health test
- Frontend build check

---

## Files Likely Affected

- backend/
- frontend/
- docker-compose.yml
- .env.example
- README.md

---

## Architecture Rules

- Do not bypass documented module boundaries.
- Keep the Strategy / Agent -> TradingDecision -> RiskCheck -> Execution pipeline intact.
- Do not introduce real-money trading.
- Update documentation if contracts, schemas, or behavior change.
