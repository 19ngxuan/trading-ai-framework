# Agent Workflow

## 1. Purpose

This document defines the expected workflow for AI coding agents working on Trading Lab.

The workflow is designed to support iterative implementation while preserving architecture, domain rules, API contracts, database consistency, and safety constraints.

---

## 2. Standard Task Workflow

For every implementation task, follow this sequence:

1. Read the task file.
2. Read relevant architecture, domain, API, database, backend, frontend, and implementation documents.
3. Restate the task goal.
4. Identify affected modules and files.
5. Create a short implementation plan.
6. Implement the smallest coherent change.
7. Add or update tests.
8. Run relevant checks.
9. Update documentation if required.
10. Summarize changes and remaining risks.

---

## 3. Planning Step

Before modifying files, the agent should produce a concise implementation plan.

The plan should include:

- task name
- relevant docs
- affected backend modules
- affected frontend modules, if any
- affected database schema, if any
- expected tests
- possible edge cases

Example:

```text
Task: M4 Moving Average Strategy
Relevant docs:
- docs/02_domain/business-rules.md
- docs/06_backend/service-contracts.md
- docs/07_implementation/tasks/M4-moving-average-strategy.md

Affected files:
- backend/app/modules/strategies/moving_average.py
- backend/app/modules/strategies/factory.py
- backend/tests/modules/strategies/test_moving_average.py

Risk:
- Must not execute orders directly.
- Must only return TradingDecision.
```

---

## 4. Implementation Step

During implementation, the agent must:

- keep changes scoped to the task
- follow service contracts
- use existing module boundaries
- preserve auditability
- keep errors explicit
- avoid speculative features
- avoid broad refactors unless requested

If a change requires a new architectural decision, stop and follow `change-process.md`.

---

## 5. Testing Step

After implementation, the agent must run relevant tests whenever possible.

Backend examples:

```text
pytest
pytest backend/tests/modules/risk/
pytest backend/tests/modules/strategies/
pytest backend/tests/api/
```

Frontend examples:

```text
npm run test
npm run lint
npm run build
```

If tests cannot be run, the agent must state:

- which tests were not run
- why they were not run
- what should be run manually

---

## 6. Documentation Step

Documentation must be updated when the task changes:

- API endpoints
- request or response shapes
- database schema
- domain entities
- workflow behavior
- business rules
- architecture decisions
- service contracts
- task acceptance criteria

Documentation should not be updated for purely internal refactors unless the documented behavior or architecture changes.

---

## 7. Completion Report

At the end of a task, the agent should report:

```text
Implemented:
- ...

Files changed:
- ...

Tests:
- ...

Not run:
- ...

Docs updated:
- ...

Notes / risks:
- ...
```

The completion report must not claim success for tests that were not actually run.

---

## 8. Handling Ambiguity

If a task is ambiguous, the agent must ask a question before implementing if the ambiguity affects:

- architecture
- data model
- API contract
- Risk Engine behavior
- broker integration
- agent decision flow
- security or safety constraints

For minor implementation details that do not affect architecture or contracts, the agent may choose the simplest documented-consistent approach.

---

## 9. Iterative Development Rule

Prefer small, complete increments.

A good increment:

- implements one capability
- has tests
- follows documented contracts
- does not create hidden design debt
- can be reviewed independently

A bad increment:

- changes many unrelated modules
- introduces unrequested abstractions
- changes API shape silently
- bypasses audit or risk controls
- adds speculative future features
