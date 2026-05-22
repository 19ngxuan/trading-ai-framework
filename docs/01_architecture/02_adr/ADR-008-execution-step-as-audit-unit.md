# ADR-008: ExecutionStep as Audit Unit

## Status

Accepted

## Context

Trading Lab must make every strategy and agent decision auditable.

For each execution step, the system needs to preserve:

- market data used as input
- strategy or agent decision
- risk validation result
- order result
- trade result
- portfolio snapshot
- metric snapshot
- agent logs
- system events

Without a central audit unit, these records can become difficult to connect and reason about.

## Decision

Every strategy or agent execution is represented as an `ExecutionStep`.

`ExecutionStep` is the central audit unit of the system.

All artifacts produced during one execution are linked to the corresponding ExecutionStep.

## Rationale

This provides a clear and traceable execution history.

A trade can be traced back through:

```text
Trade
→ Order
→ RiskCheck
→ TradingDecision
→ MarketDataSnapshot
→ ExecutionStep
→ Experiment
```

This is essential for:

- debugging
- agent decision inspection
- metrics validation
- broker sync analysis
- reproducibility
- auditability

## Alternatives Considered

### Store only trades and metrics

Rejected.

This would lose information about decisions, risk checks, and market data inputs.

### Link records only by experiment and timestamp

Rejected.

Timestamps are not a strong enough relationship model and make auditing fragile.

### Use logs only

Rejected.

Logs are not sufficient as a structured domain model.

## Consequences

### Positive

- strong auditability
- clear data relationships
- easier debugging
- better testability
- consistent execution model
- supports historical, scheduled, and manual steps

### Negative

- more persisted records
- more complex database model
- every execution path must consistently create and update ExecutionStep

## Implementation Rules

- Every historical, scheduled, or manual run must create an ExecutionStep.
- ExecutionStep must have a status.
- ExecutionStep should record trigger type.
- ExecutionStep should be linked to all artifacts produced during the step.
- Failed or skipped steps must still be persisted.
- Agent logs must link to ExecutionStep.
- System events should link to ExecutionStep where applicable.

## Related Documents

- `../system-overview.md`
- `../01_c4-model/c4-component.md`
- `../decisions.md`
- `../../02_domain/01_entities.md`
- `../../02_domain/02_workflows.md`
