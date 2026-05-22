# M6: Dashboard and Detail UI

## Goal

Build the initial frontend for experiment creation, dashboard monitoring, and detail inspection.

---

## Scope

- Create app layout with sidebar
- Build DashboardPage
- Build CreateExperimentPage
- Build ExperimentDetailPage
- Add KPI cards and experiment table
- Add charts for portfolio value/return
- Add trades and metrics tabs
- Use TanStack Query polling

---

## Out of Scope

- No compare screen yet
- No full agent log UI yet

---

## Relevant Docs

- docs/06_frontend/ui-routes.md
- docs/06_frontend/components.md
- docs/04_api/api-spec.md

---

## Acceptance Criteria

- User can create experiment from UI
- Dashboard shows experiments
- Detail page shows metrics, trades, and chart
- Start/Pause/Stop actions available where appropriate

---

## Test Requirements

- Component tests for table/form/actions
- Frontend build passes

---

## Files Likely Affected

- frontend/src/pages/
- frontend/src/features/
- frontend/src/api/

---

## Architecture Rules

- Do not bypass documented module boundaries.
- Keep the Strategy / Agent -> TradingDecision -> RiskCheck -> Execution pipeline intact.
- Do not introduce real-money trading.
- Update documentation if contracts, schemas, or behavior change.
