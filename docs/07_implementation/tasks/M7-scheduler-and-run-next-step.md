# M7: Scheduler and Run Next Step

## Goal

Add integrated scheduler and manual execution-step triggering.

---

## Scope

- Integrate APScheduler
- Implement run-next-step endpoint
- Trigger scheduled experiments
- Prevent concurrent steps for same experiment
- Support HISTORICAL/SCHEDULED/MANUAL trigger types

---

## Out of Scope

- No separate worker service
- No Redis/Celery

---

## Relevant Docs

- docs/01_architecture/decisions.md
- docs/06_backend/module-structure.md

---

## Acceptance Criteria

- Manual run creates exactly one ExecutionStep
- Scheduler triggers due experiments
- Concurrent runs for same experiment are blocked

---

## Test Requirements

- Scheduler unit/integration tests
- Run-next-step API test

---

## Files Likely Affected

- backend/app/modules/scheduler/
- backend/app/modules/execution/

---

## Architecture Rules

- Do not bypass documented module boundaries.
- Keep the Strategy / Agent -> TradingDecision -> RiskCheck -> Execution pipeline intact.
- Do not introduce real-money trading.
- Update documentation if contracts, schemas, or behavior change.
