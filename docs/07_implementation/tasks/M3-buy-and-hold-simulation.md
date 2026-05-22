# M3: Buy and Hold Simulation

## Goal

Implement the first historical simulation path with Buy and Hold.

---

## Scope

- Implement ExecutionStep creation
- Implement mock/fixture market data provider
- Implement BuyAndHoldStrategy
- Implement SimulationExecutionProvider
- Persist decisions, risk checks, orders, trades, portfolio snapshots
- Mark historical simulation completed

---

## Out of Scope

- No Moving Average strategy
- No real Alpaca integration
- No frontend requirement beyond API visibility

---

## Relevant Docs

- docs/01_architecture/c4-component.md
- docs/02_domain/workflows.md
- docs/06_backend/service-contracts.md

---

## Acceptance Criteria

- BUY_AND_HOLD historical experiment runs to completion
- ExecutionSteps are persisted
- Trade and PortfolioSnapshot records are created
- Every decision has a RiskCheck

---

## Test Requirements

- Strategy unit tests
- Execution orchestrator integration test

---

## Files Likely Affected

- backend/app/modules/execution/
- backend/app/modules/strategies/
- backend/app/modules/market_data/

---

## Architecture Rules

- Do not bypass documented module boundaries.
- Keep the Strategy / Agent -> TradingDecision -> RiskCheck -> Execution pipeline intact.
- Do not introduce real-money trading.
- Update documentation if contracts, schemas, or behavior change.
