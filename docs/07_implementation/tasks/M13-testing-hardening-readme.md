# M13: Testing, Hardening, and README

## Goal

Stabilize the project, expand tests, and make the repository presentable.

---

## Scope

- Add missing unit tests
- Add integration tests for key flows
- Add Playwright E2E demo flow if UI stable
- Finalize Docker Compose
- Write README setup and architecture summary
- Verify docs alignment

---

## Out of Scope

- No new product features unless needed for completion

---

## Relevant Docs

- docs/07_implementation/acceptance-criteria.md
- docs/07_implementation/coding-standards.md

---

## Acceptance Criteria

- Tests pass
- docker compose up works
- README explains setup
- Architecture and docs are consistent

---

## Test Requirements

- Full backend test run
- Frontend build/test
- Optional E2E demo test

---

## Files Likely Affected

- README.md
- backend/tests/
- frontend/src/**/*.test.tsx
- docs/

---

## Architecture Rules

- Do not bypass documented module boundaries.
- Keep the Strategy / Agent -> TradingDecision -> RiskCheck -> Execution pipeline intact.
- Do not introduce real-money trading.
- Update documentation if contracts, schemas, or behavior change.
