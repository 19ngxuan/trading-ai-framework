# ADR-009: Paper Trading Only in V1

## Status

Accepted

## Context

Trading Lab is an experimentation platform for evaluating rule-based and agentic-AI trading strategies.

The system will integrate with Alpaca Paper Trading in Version 1. Since the system includes automated decisions and LLM-generated outputs, supporting real-money trading would introduce substantial financial, safety, legal, and operational risk.

## Decision

Version 1 supports only:

- internal simulation
- paper trading

Version 1 must not support real-money trading.

Live-trading endpoints must not be used.

## Rationale

Paper trading is sufficient to evaluate the system's core technical goals:

- strategy execution
- agentic decision loops
- risk validation
- broker integration
- performance tracking
- auditability

Real-money trading is explicitly outside the purpose of Version 1.

## Alternatives Considered

### Add real-money trading behind a flag

Rejected.

Feature flags can be misconfigured. V1 should not include real-money execution paths at all.

### Allow manual confirmation for real trades

Rejected for V1.

The system is not yet designed for production trading safety, compliance, monitoring, or operational risk.

### Build real trading first

Rejected.

The system must prove itself in simulation and paper trading before any live trading can be considered.

## Consequences

### Positive

- lower financial risk
- safer experimentation
- simpler compliance posture
- easier development and testing
- clearer project scope

### Negative

- system cannot be used for live trading
- real-world execution constraints are only partially represented
- future live trading would require additional architecture, safety, and compliance work

## Implementation Rules

- Only paper-trading broker endpoints may be configured.
- Live-trading endpoints must be rejected or blocked.
- Environment configuration must clearly distinguish paper trading from live trading.
- Broker adapter must validate that paper-trading mode is active.
- Documentation must state that V1 is not financial advice and not a live trading system.
- Tests should verify live endpoint blocking.

## Related Documents

- `../system-overview.md`
- `../c4-context.md`
- `../c4-container.md`
- `../decisions.md`
- `../../02_domain/business-rules.md`
