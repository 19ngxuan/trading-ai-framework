# Definition of Done

## 1. Purpose

This document defines when an implementation task is considered complete.

A task is not done merely because code was written. A task is done only when implementation, tests, documentation, and architecture compliance have been addressed.

---

## 2. General Definition of Done

A task is complete only if:

1. The requested behavior is implemented.
2. The implementation is scoped to the task.
3. Existing architecture rules are respected.
4. Relevant service contracts are respected.
5. Relevant tests are added or updated.
6. Existing tests pass, or failures are clearly reported.
7. API contracts are updated if changed.
8. Database migrations are added if schema changes.
9. Documentation is updated if behavior, architecture, schema, or API contracts changed.
10. No guardrails are violated.
11. No secrets are added to source code or logs.
12. The final response summarizes changes and remaining risks.

---

## 3. Backend Task Completion Criteria

For backend tasks, the task is complete only if applicable items are satisfied:

- API route delegates to service layer.
- Business logic is not implemented in route handlers.
- Domain objects and enums are used consistently.
- Persistence goes through repositories or documented persistence abstractions.
- Strategy implementations only return `TradingDecision`.
- Agent implementations only return `TradingDecision`.
- Risk Engine is invoked before execution.
- Execution creates audit artifacts.
- Errors use documented error structure.
- Unit tests cover core logic.
- Integration tests cover API or execution flow where relevant.

---

## 4. Frontend Task Completion Criteria

For frontend tasks, the task is complete only if applicable items are satisfied:

- UI calls only Backend API endpoints.
- No trading logic exists in frontend.
- No broker or LLM calls exist in frontend.
- API types match documented responses.
- Loading and error states are handled.
- Forms validate required inputs.
- Components are organized in the documented feature structure.
- Relevant component tests are added where appropriate.
- Build passes.

---

## 5. Database Task Completion Criteria

For database tasks, the task is complete only if:

- SQLAlchemy model changes are implemented.
- Alembic migration is added.
- `docs/04_database/schema.dbml` is updated.
- Domain documentation is updated if meaning changes.
- Foreign keys preserve auditability.
- Indexes are added where needed for query patterns.
- Existing data integrity assumptions remain valid.

---

## 6. Agentic-AI Task Completion Criteria

For agentic-AI tasks, the task is complete only if:

- Agent input is explicit and structured.
- Prompt construction is isolated.
- LLM calls go through the LLM client abstraction.
- Raw outputs are logged.
- Parsed outputs are logged.
- Invalid output triggers repair logic.
- Failed repair falls back to `HOLD`.
- Agent output is converted into `TradingDecision`.
- Agent does not call broker or execution modules directly.
- Agent decision passes through Risk Engine.
- Tests cover valid output, invalid output, repair, and fallback.

---

## 7. Trading Execution Task Completion Criteria

For execution-related tasks, the task is complete only if:

- `ExecutionStep` is created.
- Market data snapshot is stored.
- Trading decision is stored.
- Risk check is stored.
- Order is stored when applicable.
- Trade is stored when applicable.
- Portfolio is updated.
- Portfolio snapshot is stored.
- Metric snapshot is stored.
- System event logs are stored for relevant events.
- HOLD does not create executable orders.
- Errors do not cause unsafe trades.

---

## 8. Documentation Completion Criteria

Documentation must be updated if the task changes:

- architecture
- domain entities
- business rules
- workflows
- API endpoints
- API schemas
- database schema
- service contracts
- frontend routes
- implementation tasks
- guardrails

Documentation updates must be consistent across affected files.

---

## 9. Testing Completion Criteria

At minimum, the agent must state:

- tests added
- tests changed
- tests run
- tests not run
- reason tests were not run

Do not claim that tests passed unless they were executed.

---

## 10. Final Report Template

At task completion, use this structure:

```text
Implemented:
- ...

Files changed:
- ...

Tests run:
- ...

Tests not run:
- ...

Docs updated:
- ...

Architecture/guardrail check:
- ...

Remaining risks:
- ...
```
