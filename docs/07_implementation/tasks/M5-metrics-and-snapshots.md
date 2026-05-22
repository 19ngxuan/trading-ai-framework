# M5: Metrics and Snapshots

## Goal

Implement portfolio snapshots and metric snapshots after every execution step.

---

## Scope

- Calculate total return
- Calculate profit/loss
- Calculate number of trades
- Calculate max drawdown
- Calculate Buy-and-Hold comparison when benchmark exists
- Expose metrics and portfolio snapshot endpoints

---

## Out of Scope

- No Sharpe/Sortino in V1
- No advanced analytics

---

## Relevant Docs

- docs/02_domain/entities.md
- docs/03_api/api-spec.md
- docs/06_backend/service-contracts.md

---

## Acceptance Criteria

- Every completed step has PortfolioSnapshot and MetricSnapshot
- Max drawdown is correct for deterministic fixtures
- Metrics API returns time series

---

## Test Requirements

- Metrics unit tests
- API tests for metrics endpoints

---

## Files Likely Affected

- backend/app/modules/metrics/
- backend/app/api/routes/metrics.py

---

## Architecture Rules

- Do not bypass documented module boundaries.
- Keep the Strategy / Agent -> TradingDecision -> RiskCheck -> Execution pipeline intact.
- Do not introduce real-money trading.
- Update documentation if contracts, schemas, or behavior change.
