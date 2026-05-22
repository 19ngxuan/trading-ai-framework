# ADR-007: Alpaca behind Adapters

## Status

Accepted

## Context

Trading Lab uses Alpaca in Version 1 for:

- market data
- paper trading

However, external provider logic should not leak into core domain logic. Strategies, agents, risk checks, and API routes should not depend directly on Alpaca-specific APIs, payloads, or client details.

## Decision

Alpaca integrations must be isolated behind adapter modules.

The expected adapters are:

- `AlpacaMarketDataProvider`
- `AlpacaBrokerAdapter`

Market data access goes through the Market Data Module.

Broker access goes through the Broker Module.

## Rationale

This keeps external provider concerns isolated and replaceable.

Benefits:

- strategy code remains provider-independent
- agent code remains provider-independent
- broker switching is possible later
- market data switching is possible later
- testing is easier with mock adapters
- external API changes are isolated

## Alternatives Considered

### Call Alpaca directly from strategies

Rejected.

This would tightly couple strategies to one provider and break testability.

### Call Alpaca directly from API routes

Rejected.

Routes should not contain integration or business logic.

### Use only Alpaca-specific domain models

Rejected.

The system needs provider-independent domain models such as MarketDataSnapshot, TradingDecision, Order, and Trade.

## Consequences

### Positive

- provider isolation
- easier testing
- cleaner domain model
- later replaceability
- safer architecture boundaries

### Negative

- requires adapter interfaces
- requires mapping between Alpaca responses and domain objects
- adds some initial implementation overhead

## Implementation Rules

- Market data must be fetched through Market Data Module.
- Paper orders must be submitted through Broker Module.
- Strategies must not call Alpaca.
- Agents must not call Alpaca.
- API Routes must not call Alpaca directly.
- Alpaca response payloads must be mapped to internal domain objects.
- Only paper-trading endpoints may be used in V1.
- Live trading endpoints must be blocked or rejected.

## Related Documents

- `../system-overview.md`
- `../c4-container.md`
- `../c4-component.md`
- `../decisions.md`
- `../../06_backend/service-contracts.md`
