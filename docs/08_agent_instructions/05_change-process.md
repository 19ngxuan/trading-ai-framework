# Change Process

## 1. Purpose

This document defines how design, architecture, data model, API, and safety changes must be handled.

The goal is to prevent silent architecture drift and uncontrolled changes by coding agents.

---

## 2. What Counts as a Design Change

A change is considered a design change if it affects any of the following:

- architecture style
- module boundaries
- execution pipeline
- domain model
- database schema
- API contract
- frontend route structure
- service contracts
- Risk Engine behavior
- broker integration
- market data integration
- LLM or agent workflow
- security rules
- safety rules
- auditability guarantees

---

## 3. Changes That Require Confirmation

The coding agent must request confirmation before implementing changes involving:

- new database tables
- removed database tables
- changed foreign key relationships
- changed enum values
- new API endpoints
- changed API request or response shapes
- new external services
- new backend modules
- new frontend top-level routes
- changes to Risk Engine rules
- changes to the strategy-agent-risk-execution pipeline
- direct broker access from new locations
- real-money trading support
- live-trading endpoints
- multi-user support
- authentication
- multi-asset trading
- short selling
- margin trading
- options trading

---

## 4. Required Change Proposal Format

If a change is needed, the coding agent must stop and produce a proposal.

Use this format:

```text
Design change required.

Current rule or design:
- ...

Problem:
- ...

Proposed change:
- ...

Alternatives considered:
- ...

Affected documents:
- ...

Affected code areas:
- ...

Risks:
- ...

Request:
Please confirm whether this change should be implemented.
```

Do not implement the change until confirmation is given.

---

## 5. Updating ADRs

If the change affects architecture decisions, update or create an ADR.

ADR statuses:

- `Proposed`
- `Accepted`
- `Deprecated`
- `Superseded`

If an existing ADR is replaced, do not delete it. Mark it as superseded and link to the new ADR.

---

## 6. Updating Documentation

The following documents must be kept consistent:

Architecture changes:

- `docs/01_architecture/system-overview.md`
- `docs/01_architecture/decisions.md`
- relevant ADR files
- C4 documents if boundaries change

Domain changes:

- `docs/02_domain/entities.md`
- `docs/02_domain/workflows.md`
- `docs/02_domain/business-rules.md`

API changes:

- `docs/03_api/api-spec.md`
- `docs/03_api/openapi.yaml`

Database changes:

- `docs/04_database/schema.dbml`
- `docs/04_database/migrations.md`

Frontend changes:

- `docs/05_frontend/ui-routes.md`
- `docs/05_frontend/components.md`

Backend changes:

- `docs/06_backend/module-structure.md`
- `docs/06_backend/service-contracts.md`

Implementation changes:

- `docs/07_implementation/task-breakdown.md`
- relevant task files
- `docs/07_implementation/acceptance-criteria.md`

Agent rules changes:

- `docs/08_agent/instructions.md`
- `docs/08_agent/workflow.md`
- `docs/08_agent/guardrails.md`
- `docs/08_agent/definition-of-done.md`
- `docs/08_agent/change-process.md`

---

## 7. Safe Changes That Usually Do Not Require Confirmation

The agent may usually proceed without confirmation for:

- adding tests
- fixing typos
- improving error messages without API contract changes
- internal refactors that preserve public behavior
- adding small helper functions
- improving type annotations
- improving local code organization within existing modules
- adding logging that does not expose secrets
- fixing bugs to match documented behavior

If uncertain, ask before proceeding.

---

## 8. Rollback Expectations

If a change fails or violates documentation:

1. Stop.
2. Explain what failed.
3. Identify affected files.
4. Propose rollback or correction.
5. Do not hide partial failures.

---

## 9. Principle

Architecture can evolve, but it must evolve explicitly.

No silent changes to:

```text
Strategy / Agent
→ TradingDecision
→ RiskEngine
→ ExecutionEngine
→ Simulation or Paper Broker
```

No silent changes to:

```text
Version 1 = simulation and paper trading only.
```
