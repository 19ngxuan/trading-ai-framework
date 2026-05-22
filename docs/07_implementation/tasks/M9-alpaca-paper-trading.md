# M9: Alpaca Paper Trading

## Goal

Integrate Alpaca Paper Trading behind the Broker Module and paper execution provider.

---

## Scope

- Implement AlpacaBrokerAdapter
- Implement PaperExecutionProvider
- Submit paper orders
- Fetch order status
- Fetch account and positions
- Write BrokerSyncLog
- Pause experiment on broker-state mismatch
- Block live endpoints

---

## Out of Scope

- No real-money trading
- No strategy-to-broker calls

---

## Relevant Docs

- docs/01_architecture/adr/ADR-009-paper-trading-only.md
- docs/02_domain/business-rules.md
- docs/06_backend/service-contracts.md

---

## Acceptance Criteria

- PAPER_TRADING experiment can place paper order
- Broker state is synced
- Mismatch pauses experiment
- Only paper endpoint accepted

---

## Test Requirements

- Broker adapter tests with mocked HTTP
- Mismatch integration test

---

## Files Likely Affected

- backend/app/modules/broker/
- backend/app/modules/execution/

---

## Architecture Rules

- Do not bypass documented module boundaries.
- Keep the Strategy / Agent -> TradingDecision -> RiskCheck -> Execution pipeline intact.
- Do not introduce real-money trading.
- Update documentation if contracts, schemas, or behavior change.
