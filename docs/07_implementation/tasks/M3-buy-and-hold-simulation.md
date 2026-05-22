# M3: Buy and Hold Simulation

## Goal

Implement the first historical simulation path with Buy and Hold.

---

## Scope

- Implement ExecutionStep creation
- Implement deterministic local SPY daily CSV fixture loader
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

- docs/01_architecture/01_c4-model/c4-component.md
- docs/02_domain/02_workflows.md
- docs/05_backend/service-contracts.md

---

## Acceptance Criteria

- BUY_AND_HOLD historical experiment runs to completion
- Historical simulation runs as a FastAPI in-process background task. No external queue or worker is used. Frontend/API consumers observe progress through polling persisted execution state.
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
