# Database Migrations

## 1. Purpose

This document defines how database schema changes are managed for Trading Lab.

The goal is to keep the PostgreSQL schema, SQLAlchemy models, Alembic migrations, DBML documentation, API contracts, and domain documentation consistent.

This file is intended for developers and AI coding agents working on database-related changes.

---

## 2. Migration Tool

Trading Lab uses Alembic for database migrations.

Expected backend stack:

- PostgreSQL
- SQLAlchemy
- Alembic
- FastAPI

Alembic migration files should be stored under the backend migration directory, typically:

```text
backend/alembic/versions/
```

The DBML reference schema is stored at:

```text
docs/03_database/schema.dbml
```

---

## 3. Source of Truth

The implementation source of truth is the active database schema generated through Alembic migrations.

The documentation source of truth is:

```text
docs/03_database/schema.dbml
```

These must remain consistent.

Any database schema change requires updates to all affected artifacts:

1. SQLAlchemy model
2. Alembic migration
3. `docs/03_database/schema.dbml`
4. `docs/02_domain/01_entities.md` if the meaning of a domain entity changes
5. `docs/04_api/api-spec.md` and `openapi.yaml` if API request or response shapes change
6. Tests affected by the change

---

## 4. Migration Rules

### Rule 1: No Model Change Without Migration

Any change to a SQLAlchemy model that affects the database schema must include an Alembic migration.

Examples:

- adding a column
- removing a column
- renaming a column
- changing a column type
- adding an index
- adding a constraint
- changing enum values
- adding a table
- removing a table

---

### Rule 2: No Migration Without DBML Update

Any Alembic migration that changes the database schema must update:

```text
docs/03_database/schema.dbml
```

The DBML must reflect the intended final schema after applying all migrations.

---

### Rule 3: Domain Meaning Changes Require Domain Documentation Updates

If a schema change changes the meaning of an entity or relationship, update:

```text
docs/02_domain/01_entities.md
```

Examples:

- adding multi-asset portfolio support
- replacing the single-position portfolio model with a Position table
- changing how Buy-and-Hold benchmark experiments are represented
- changing the relation between TradingDecision and RiskCheck

---

### Rule 4: API Shape Changes Require API Documentation Updates

If a schema change affects API request or response models, update:

```text
docs/04_api/api-spec.md
docs/04_api/openapi.yaml
```

Examples:

- adding fields to Experiment response
- changing ID type
- exposing new status values
- adding filters for new fields
- changing log payloads

---

### Rule 5: Audit Tables Must Not Be Removed Silently

The following tables are part of the audit chain and must not be removed without an explicit architecture decision:

- `execution_steps`
- `market_data_snapshots`
- `trading_decisions`
- `risk_checks`
- `orders`
- `trades`
- `portfolio_snapshots`
- `metric_snapshots`
- `agent_decision_logs`
- `broker_sync_logs`
- `system_event_logs`

If an implementation appears to require removing or bypassing any of these tables, stop and review the architecture first.

---

## 5. Initial Migration

The initial migration should create all tables and enums defined in:

```text
docs/03_database/schema.dbml
```

The initial migration should include:

- all enum types
- all core tables
- primary keys
- foreign keys
- unique constraints
- indexes
- timestamp columns
- JSON columns

The initial migration should not insert production data.

Seed data should be handled separately.

---

## 6. Enum Handling

Enums are used for stable domain concepts such as:

- experiment mode
- strategy type
- experiment status
- trading frequency
- execution step status
- trigger type
- action
- order status
- agent mode
- parsing status
- broker sync status
- system event type

Enum changes must be treated carefully.

### Adding an Enum Value

Allowed if backward-compatible.

Requirements:

- update SQLAlchemy enum definition
- create Alembic migration
- update `schema.dbml`
- update relevant documentation
- add tests for the new value if behavior changes

### Renaming an Enum Value

Potentially breaking.

Requirements:

- document migration strategy
- migrate existing data
- update API docs
- update frontend handling
- update tests

### Removing an Enum Value

Requires explicit review.

Removing enum values can break historical records and audit logs.

Do not remove enum values unless there is a clear migration plan.

---

## 7. JSON / JSONB Fields

The DBML uses `json` fields for flexible payloads.

In PostgreSQL implementation, these should typically be implemented as JSONB.

JSONB is appropriate for:

- `strategy_configs.parameters_json`
- `market_data_snapshots.raw_data_json`
- `trading_decisions.raw_decision_json`
- `risk_checks.rules_triggered_json`
- `agent_decision_logs.input_json`
- `agent_decision_logs.parsed_output_json`
- `broker_sync_logs.broker_positions_json`
- `broker_sync_logs.local_positions_json`
- `broker_sync_logs.mismatch_details_json`
- `system_event_logs.details_json`

V1 risk configuration is stored as JSONB in `strategy_configs.parameters_json.riskConfig`; no dedicated risk configuration table exists in V1.

### JSONB Rule

Core queryable fields should remain explicit columns.

Use explicit columns for:

- IDs
- timestamps
- status fields
- type fields
- action fields
- symbol
- quantity
- price
- cash
- portfolio value

Use JSONB for:

- flexible strategy-specific parameters
- raw external provider payloads
- agent inputs and outputs
- diagnostics
- event details

---

## 8. ID Strategy

The current DBML uses:

```text
id bigint [pk, increment]
```

Therefore, database and API documentation currently assume integer IDs.

If the project changes to UUIDs later, the following must be updated together:

- `schema.dbml`
- SQLAlchemy models
- Alembic migration
- API docs
- OpenAPI spec
- frontend types
- tests

Do not mix bigint IDs and UUID IDs silently.

---

## 9. Breaking Schema Changes

A breaking schema change is any change that can invalidate existing data, API contracts, or audit history.

Examples:

- renaming table or column
- changing ID type
- removing a table
- removing an enum value
- changing a relationship cardinality
- changing uniqueness constraints
- replacing the V1 single-position portfolio model with multi-position support

Breaking changes require:

1. explicit explanation
2. migration plan
3. rollback plan or statement that rollback is not supported
4. documentation updates
5. test updates

For AI coding agents: do not perform breaking schema changes without confirmation.

---

## 10. Rollback Policy

For Version 1, migrations should be designed to be simple and reviewable.

Every migration should define both upgrade and downgrade logic where practical.

Downgrades may be limited when:

- data loss would occur
- enum values were added
- JSON payloads were transformed
- historical audit records would be affected

If downgrade is not safely supported, document it in the migration comments.

---

## 11. Seed Data

Seed data should not be part of schema migrations unless it is required static reference data.

For V1, most enum values are represented as database enum types, not seed rows.

Development seed scripts may create sample experiments such as:

- Buy-and-Hold SPY historical simulation
- Moving Average SPY historical simulation
- Agentic AI simulation placeholder

Seed scripts should live outside Alembic migrations, for example:

```text
scripts/seed.sh
backend/app/scripts/seed_dev_data.py
```

---

## 12. Test Data

Automated tests should not depend on production-like external data.

Use deterministic fixtures for:

- SPY price series
- moving average values
- RSI values
- simple portfolio timelines
- known drawdown scenarios
- agent output parser cases

Database tests should use an isolated test database or transaction rollback strategy.

---

## 13. Required Checks Before Merging Database Changes

Before merging a database-related change, verify:

- SQLAlchemy models are updated.
- Alembic migration exists.
- Migration applies successfully from a clean database.
- `schema.dbml` is updated.
- Domain docs are updated if entity semantics changed.
- API docs are updated if response or request shapes changed.
- Tests are updated or added.
- Audit chain is preserved.
- RiskCheck still sits between TradingDecision and Order.

---

## 14. Critical Invariants

The database schema must preserve these invariants:

1. Each experiment has exactly one strategy configuration.
2. Each experiment has exactly one current portfolio.
3. Each execution step belongs to exactly one experiment.
4. Each execution step has at most one market data snapshot.
5. Each execution step has at most one trading decision.
6. Each trading decision has exactly one risk check.
7. Orders are created only after risk checks.
8. Trades are created from orders, and one order may have zero, one, or many trades.
9. Portfolio snapshots and metric snapshots are tied to execution steps.
10. Agent decision logs are tied to execution steps.
11. Broker sync logs are tied to paper-trading execution steps.
12. System events are tied to experiments and optionally execution steps.

These invariants support auditability and must not be weakened without an architecture review.

---

## 15. Related Documents

- `./schema.dbml`
- `../01_architecture/decisions.md`
- `../01_architecture/02_adr/ADR-008-execution-step-as-audit-unit.md`
- `../02_domain/01_entities.md`
- `../02_domain/02_workflows.md`
- `../02_domain/03_business-rules.md`
- `../04_api/api-spec.md`
- `../05_backend/module-structure.md`
- `../05_backend/service-contracts.md`
