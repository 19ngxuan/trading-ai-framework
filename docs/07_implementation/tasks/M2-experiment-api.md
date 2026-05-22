# M2: Experiment API

## Goal

Implement experiment creation, retrieval, options, and lifecycle status endpoints.

---

## Scope

- POST /api/v1/experiments
- GET /api/v1/experiments
- GET /api/v1/experiments/{id}
- POST start/pause/resume/stop
- GET /api/v1/options
- Validate status transitions
- Initialize portfolio on create
- `start` must reject `PAUSED`; `resume` handles `PAUSED`

---

## Out of Scope

- No simulation execution yet
- No Alpaca or LLM calls

---

## Relevant Docs

- docs/04_api/api-spec.md
- docs/02_domain/02_workflows.md
- docs/05_backend/service-contracts.md

---

## Acceptance Criteria

- Experiment can be created with StrategyConfig and Portfolio
- Invalid transitions return 409
- Options endpoint returns enums
- API error format is consistent

---

## Test Requirements

- API tests for create/list/detail/status transitions

---

## Files Likely Affected

- backend/app/api/routes/
- backend/app/api/schemas/
- backend/app/modules/experiments/

---

## Architecture Rules

- Do not bypass documented module boundaries.
- Keep the Strategy / Agent -> TradingDecision -> RiskCheck -> Execution pipeline intact.
- Do not introduce real-money trading.
- Update documentation if contracts, schemas, or behavior change.
