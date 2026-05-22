# M1: Domain Model and Database

## Goal

Implement the database model and migration foundation based on the DBML schema.

---

## Scope

- Add SQLAlchemy models for core entities
- Add domain enums
- Configure Alembic
- Create initial migration
- Add repository skeletons
- Add database session management

---

## Out of Scope

- No business logic in repositories
- No API endpoints beyond what is necessary for setup

---

## Relevant Docs

- docs/02_domain/entities.md
- docs/04_database/schema.dbml
- docs/04_database/migrations.md

---

## Acceptance Criteria

- Alembic migration applies cleanly
- Tables match schema.dbml
- Repository can save/load Experiment
- No undocumented schema changes

---

## Test Requirements

- Repository tests
- Migration smoke test

---

## Files Likely Affected

- backend/app/domain/
- backend/app/persistence/
- backend/alembic/

---

## Architecture Rules

- Do not bypass documented module boundaries.
- Keep the Strategy / Agent -> TradingDecision -> RiskCheck -> Execution pipeline intact.
- Do not introduce real-money trading.
- Update documentation if contracts, schemas, or behavior change.
