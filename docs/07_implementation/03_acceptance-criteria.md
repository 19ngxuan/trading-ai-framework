# Acceptance Criteria

## 1. Purpose

This document defines global acceptance criteria for implementation tasks.

A task is only complete when it satisfies the functional goal, preserves architecture rules, includes necessary tests, and updates documentation when needed.

---

## 2. Global Definition of Done

A task is done only if:

- the requested behavior is implemented
- code follows the documented module boundaries
- no architecture rule is violated
- no safety rule is bypassed
- tests are added or updated where appropriate
- existing tests pass
- API contracts remain consistent with `docs/04_api/api-spec.md`
- database changes include Alembic migrations
- database changes are reflected in `docs/03_database/schema.dbml`
- domain changes are reflected in `docs/02_domain/01_entities.md`
- relevant README or docs are updated when behavior changes

---

## 3. Backend Acceptance Criteria

Backend tasks must satisfy:

- API routes delegate to services/modules
- business logic does not live in route handlers
- repositories encapsulate database access
- strategies and agents only return `TradingDecision`
- every executable decision passes through Risk Engine
- all execution steps are persisted
- important failures create system events
- external services are called only through adapters/clients

---

## 4. Frontend Acceptance Criteria

Frontend tasks must satisfy:

- UI calls only backend APIs
- no trading logic is implemented in frontend
- loading and error states are handled
- API errors are displayed in a useful way
- TypeScript types are used for API data
- polling is implemented through TanStack Query where needed
- components remain reusable and feature-scoped

---

## 5. Database Acceptance Criteria

Database tasks must satisfy:

- SQLAlchemy model changes are accompanied by Alembic migrations
- migrations can be applied from a clean database
- relationships match the DBML schema
- audit entities are preserved
- enum changes are deliberate and documented
- JSON fields are used only for flexible or diagnostic data

---

## 6. Testing Acceptance Criteria

A task should include tests for:

- deterministic domain logic
- error cases
- risk and safety behavior
- API behavior when endpoints are changed
- persistence behavior when schema or repositories change

External services must be mocked in regular tests.

---

## 7. Architecture Change Criteria

If a task requires changing any of the following, implementation must stop until the design is updated and confirmed:

- module boundaries
- execution pipeline
- data model
- API contract
- Risk Engine behavior
- Broker integration
- Market Data integration
- Agentic-AI workflow
- security or safety rules
