# ADR-004: Agentic AI as Strategy

## Status

Accepted

## Context

Trading Lab supports both rule-based strategies and agentic-AI decision systems.

Rule-based strategies include:

- Buy and Hold
- Moving Average

Agentic-AI strategies may include:

- Single-Agent decision mode
- Pipeline-Agent mode
- Market Analyst Agent
- Trading Decision Agent
- Agent Risk Manager

A design risk is that agentic-AI components could become a separate execution path and bypass the same safety, risk, persistence, and metrics pipeline used by rule-based strategies.

## Decision

Agentic AI will be integrated as a strategy type.

From the perspective of the execution pipeline, an agentic-AI strategy behaves like any other strategy:

```text
Strategy / Agent
→ TradingDecision
→ RiskEngine
→ ExecutionEngine
→ Simulation or Paper Trading
```

Agentic AI must produce a standardized `TradingDecision`.

It must not execute orders directly.

## Rationale

This decision keeps the system consistent and comparable.

Benefits:

- rule-based and AI strategies use the same execution pipeline
- all strategies are comparable through the same metrics
- risk validation is mandatory for all decisions
- order execution remains centralized
- audit logging remains consistent
- agentic AI cannot bypass safety rules

## Alternatives Considered

### Separate agent execution pipeline

Rejected.

A separate agent pipeline would make it easier for AI logic to bypass risk validation, execution rules, and audit requirements.

### Agent directly calls broker

Rejected.

This would violate the safety model and make the system difficult to audit.

### Agent as external service

Not selected for V1.

A separate agent service may be considered later, but in V1 the agent module is implemented inside the FastAPI modular monolith.

## Consequences

### Positive

- unified strategy abstraction
- consistent metrics
- consistent audit trail
- easier comparison between rule-based and agentic strategies
- strong safety boundaries

### Negative

- agentic workflows must be adapted to the strategy interface
- complex multi-agent flows must still reduce to a final TradingDecision
- additional logging is needed for agent intermediate steps

## Implementation Rules

- `AgenticAIStrategy` must implement the same conceptual strategy contract as other strategies.
- Agent outputs must be converted to standardized `TradingDecision` objects.
- Agent logs must store inputs, prompts, raw outputs, parsed outputs, and repair attempts.
- Agent decisions must pass through the system Risk Engine.
- Agent Risk Manager is not a replacement for the system Risk Engine.
- Agent Module must not call Broker Module directly.
- Agent Module must not execute orders.

## Related Documents

- `../system-overview.md`
- `../c4-component.md`
- `../decisions.md`
- `../../02_domain/business-rules.md`
- `../../06_backend/service-contracts.md`
