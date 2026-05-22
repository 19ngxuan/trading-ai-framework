# M12: Compare and Events UI

## Goal

Implement comparison screen and central events screen.

---

## Scope

- Implement compare API if not complete
- Build ComparePage
- Build experiment selector and benchmark selector
- Build comparison table and chart
- Build EventsPage
- Add event filters

---

## Out of Scope

- No advanced portfolio analytics
- No export/reporting

---

## Relevant Docs

- docs/04_api/api-spec.md
- docs/06_frontend/ui-routes.md
- docs/06_frontend/components.md

---

## Acceptance Criteria

- Multiple experiments can be compared
- Benchmark difference is displayed
- Events can be filtered by level/event type

---

## Test Requirements

- Compare API tests
- Frontend component tests for compare/events

---

## Files Likely Affected

- backend/app/api/routes/comparison.py
- frontend/src/features/comparison/
- frontend/src/features/events/

---

## Architecture Rules

- Do not bypass documented module boundaries.
- Keep the Strategy / Agent -> TradingDecision -> RiskCheck -> Execution pipeline intact.
- Do not introduce real-money trading.
- Update documentation if contracts, schemas, or behavior change.
