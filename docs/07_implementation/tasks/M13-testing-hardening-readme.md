# M13: Configurable Position Sizing

## Goal

Add configurable position sizing so experiment creators can control BUY order
size without changing strategy or agent decision logic.

---

## Scope

- Backend position sizing calculator
- API validation for position sizing config
- Frontend create-form support
- Documentation/OpenAPI alignment
- Regression tests for historical, agentic historical, and paper-trading paths

---

## Out of Scope

- No schema migration
- No new strategy behavior
- No broker behavior expansion
- No scheduler behavior changes

---

## Relevant Docs

- docs/07_implementation/03_acceptance-criteria.md
- docs/07_implementation/01_coding-standards.md

---

## Acceptance Criteria

- `ALL_IN`, `FIXED_CASH`, `PERCENT_OF_PORTFOLIO`, and `FIXED_QUANTITY` are supported.
- Existing `ALL_IN` behavior remains backward compatible.
- Position sizing affects BUY quantity only.
- SELL always liquidates the existing long SPY position and never shorts.
- Invalid create payloads return `422 VALIDATION_ERROR`.
- Position sizing details are auditable through `RiskCheck`.

---

## Test Requirements

- Position sizing unit tests
- API validation tests
- Historical Buy-and-Hold, Moving Average, Agentic-AI, and paper-trading regression tests
- Full backend PostgreSQL suite
- Frontend build

---

## Files Likely Affected

- backend/app/modules/execution/position_sizing.py
- backend/app/modules/execution/risk.py
- backend/app/api/schemas/experiment_schemas.py
- frontend/src/features/experiments/CreateExperimentForm.tsx
- docs/04_api/
- backend/tests/

---

## Architecture Rules

- Do not bypass documented module boundaries.
- Keep the Strategy / Agent -> TradingDecision -> RiskCheck -> Execution pipeline intact.
- Do not introduce real-money trading.
- Update documentation if contracts, schemas, or behavior change.
