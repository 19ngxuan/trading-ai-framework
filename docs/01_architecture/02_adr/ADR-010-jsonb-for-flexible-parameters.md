# ADR-010: PostgreSQL JSONB for Flexible Parameters

## Status

Accepted

## Context

Trading Lab contains several areas where data shape may vary across strategies, agents, providers, or event types.

Examples:

- strategy-specific parameters
- agent-specific settings
- raw LLM outputs
- parsed LLM outputs
- repair prompt metadata
- broker sync details
- event details
- provider-specific raw payloads
- raw decision data

At the same time, the core domain contains important fields that must be queryable and relationally consistent.

## Decision

PostgreSQL JSONB fields may be used for flexible, strategy-specific, agent-specific, provider-specific, or diagnostic payloads.

Core domain fields must remain explicit columns.

## Rationale

JSONB allows flexible extension without creating a new table or column for every strategy-specific or agent-specific field.

This is useful for:

- agent logs
- raw outputs
- flexible parameters
- event details
- provider payloads

However, overusing JSONB would weaken the relational model and make queries harder. Therefore, only flexible payloads use JSONB.

## Alternatives Considered

### Explicit columns for everything

Rejected.

This would make the schema rigid and require frequent migrations for small strategy or agent changes.

### JSONB for everything

Rejected.

This would weaken the relational model, reduce type clarity, and make important queries harder.

### Separate tables for each strategy type

Rejected for V1.

This would add unnecessary complexity before the strategy set stabilizes.

## Consequences

### Positive

- flexible strategy and agent configuration
- easier storage of raw diagnostic payloads
- fewer migrations for optional fields
- good balance between relational and flexible data

### Negative

- JSONB fields require discipline
- validation must happen in application code
- important fields may be harder to query if placed in JSONB incorrectly
- indexes may be needed later for frequently queried JSONB fields

## Implementation Rules

Use explicit columns for core fields such as:

- ids
- experiment id
- execution step id
- status
- mode
- strategy type
- action
- symbol
- quantity
- price
- timestamp
- portfolio value
- return metrics

Use JSONB for flexible fields such as:

- `parametersJson`
- `rawDecisionJson`
- `inputJson`
- `parsedOutputJson`
- `rulesTriggeredJson`
- `detailsJson`
- `brokerPositionsJson`
- `mismatchDetailsJson`

Do not hide core business state only in JSONB.

## Related Documents

- `../decisions.md`
- `../../02_domain/01_entities.md`
- `../../03_database/schema.dbml`
