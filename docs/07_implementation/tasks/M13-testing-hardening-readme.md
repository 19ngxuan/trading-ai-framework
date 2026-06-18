# M13: RiskCheck Sizing Cleanup

## Goal

Keep executable quantity control inside RiskCheck so strategies and agents only
propose `BUY`, `SELL`, or `HOLD`.

---

## Scope

- Backend RiskCheck sizing behavior
- API schema cleanup
- Frontend create-form cleanup
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

- BUY uses available cash and whole-share rounding.
- SELL always liquidates the existing long SPY position and never shorts.
- Quantity decisions are auditable through `RiskCheck`.

---

## Test Requirements

- RiskCheck sizing regression tests
- API validation tests
- Historical Buy-and-Hold, Moving Average, Agentic-AI, and paper-trading regression tests
- Full backend PostgreSQL suite
- Frontend build

---

## Files Likely Affected

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
