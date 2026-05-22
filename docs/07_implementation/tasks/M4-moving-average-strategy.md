# M4: Moving Average Strategy

## Goal

Implement the 200-day Moving Average strategy and make it executable in historical simulation.

---

## Scope

- Implement MovingAverageStrategy
- Calculate/use moving_average from snapshots
- Generate BUY/SELL/HOLD decisions
- Respect ALL_IN position sizing through Risk Engine
- Persist decisions and trades

---

## Out of Scope

- No advanced indicators except needed MA
- No parameter sweeps

---

## Relevant Docs

- docs/02_domain/03_business-rules.md
- docs/05_backend/service-contracts.md

---

## Acceptance Criteria

- BUY when price > MA and no position
- SELL when price < MA and position exists
- HOLD otherwise
- All actions pass through Risk Engine

---

## Test Requirements

- MovingAverageStrategy unit tests
- Historical simulation integration test

---

## Files Likely Affected

- backend/app/modules/strategies/
- backend/app/modules/risk/

---

## Architecture Rules

- Do not bypass documented module boundaries.
- Keep the Strategy / Agent -> TradingDecision -> RiskCheck -> Execution pipeline intact.
- Do not introduce real-money trading.
- Update documentation if contracts, schemas, or behavior change.
