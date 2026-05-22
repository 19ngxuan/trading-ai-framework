# M8: Alpaca Market Data

## Goal

Integrate Alpaca as the market data provider behind an adapter.

---

## Scope

- Implement AlpacaMarketDataProvider
- Load credentials from environment
- Fetch historical SPY data
- Fetch latest SPY data
- Map provider data to MarketDataSnapshot inputs
- Handle missing data with SKIPPED step and event

---

## Out of Scope

- No broker order execution
- No direct Alpaca calls outside market_data module

---

## Relevant Docs

- docs/01_architecture/02_adr/ADR-007-alpaca-behind-adapters.md
- docs/05_backend/service-contracts.md

---

## Acceptance Criteria

- Market data provider interface is preserved
- Alpaca-specific code isolated
- Missing data produces SystemEventLog

---

## Test Requirements

- Provider tests with mocked HTTP
- Missing data test

---

## Files Likely Affected

- backend/app/modules/market_data/
- backend/app/core/config.py

---

## Architecture Rules

- Do not bypass documented module boundaries.
- Keep the Strategy / Agent -> TradingDecision -> RiskCheck -> Execution pipeline intact.
- Do not introduce real-money trading.
- Update documentation if contracts, schemas, or behavior change.
