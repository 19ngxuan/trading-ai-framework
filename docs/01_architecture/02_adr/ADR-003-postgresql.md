# ADR-003: PostgreSQL Database

## Status

Accepted

## Context

Trading Lab needs to persist structured and audit-heavy domain data:

- experiments
- strategy configurations
- portfolios
- execution steps
- market data snapshots
- trading decisions
- risk checks
- orders
- trades
- portfolio snapshots
- metric snapshots
- agent decision logs
- broker sync logs
- system events

The system also requires flexible fields for strategy-specific parameters, agent inputs, raw LLM outputs, parsed outputs, provider response details, and event metadata.

## Decision

PostgreSQL will be used as the primary database for Version 1.

Relational tables will store core domain entities. JSONB fields may be used for flexible payloads.

## Rationale

PostgreSQL fits the domain well because the system is relational and audit-oriented.

Important properties:

- strong relational modeling
- transaction support
- indexing support
- JSONB support
- good tooling
- compatibility with SQLAlchemy and Alembic
- suitable for both operational state and later analysis

## Alternatives Considered

### SQLite

SQLite would be simpler for local development, but it is less suitable for the intended relational model, concurrent access patterns, JSONB usage, and later evolution.

### MongoDB

MongoDB would make flexible documents easy, but the domain contains many relational links and audit chains. PostgreSQL with JSONB provides a better balance.

### In-memory storage

Rejected because the system requires persistent experiment history, audit logs, metrics, and reproducibility.

## Consequences

### Positive

- strong consistency
- relational modeling for audit chains
- JSONB flexibility
- good migration tooling
- good fit for Docker Compose
- later analytical queries are possible

### Negative

- requires schema management
- migrations must be maintained
- JSONB usage must be disciplined
- relational complexity must be managed carefully

## Implementation Rules

- Core searchable fields must be explicit columns.
- Flexible optional details may use JSONB.
- Database schema changes must be handled through Alembic migrations.
- Business logic must not be hidden inside repositories.
- Every executed trade must remain traceable through persisted records.
- The database must not be accessed directly by the frontend.
- The backend is the only owner of database access.

## Related Documents

- `../system-overview.md`
- `../01_c4-model/c4-container.md`
- `../01_c4-model/c4-component.md`
- `../decisions.md`
- `../../03_database/schema.dbml`
