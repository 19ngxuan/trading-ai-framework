# Agent Instructions

## 1. Purpose

This document defines the general working instructions for AI coding agents working on the Trading Lab repository.

It applies to tools such as Codex, Claude Code, Cursor agents, or any other coding assistant that modifies source code, documentation, tests, database schemas, or configuration.

The goal is to keep implementation aligned with the documented architecture and to prevent uncontrolled architecture drift.

---

## 2. Required Reading Before Changes

Before modifying code, the coding agent must read the documents relevant to the task.

At minimum, the agent must inspect:

- `docs/01_architecture/system-overview.md`
- `docs/01_architecture/decisions.md`
- `docs/02_domain/entities.md`
- `docs/02_domain/workflows.md`
- `docs/02_domain/business-rules.md`
- `docs/06_backend/module-structure.md`
- `docs/06_backend/service-contracts.md`
- the specific task file under `docs/07_implementation/tasks/`

If the task touches API contracts, read:

- `docs/03_api/api-spec.md`
- `docs/03_api/openapi.yaml`

If the task touches database schema or persistence, read:

- `docs/04_database/schema.dbml`
- `docs/04_database/migrations.md`

If the task touches frontend behavior, read:

- `docs/05_frontend/ui-routes.md`
- `docs/05_frontend/components.md`

---

## 3. General Working Rules

The coding agent must:

1. Implement only the requested task or explicitly confirmed follow-up work.
2. Preserve existing architecture boundaries.
3. Avoid introducing new modules, services, tables, endpoints, or external dependencies unless the task explicitly requires them.
4. Ask for clarification if the task conflicts with the documentation.
5. Stop before implementing if a design change is required.
6. Keep changes small and reviewable.
7. Add or update tests for behavior changes.
8. Update documentation when public contracts, schemas, workflows, or architecture rules change.
9. Summarize what was changed and what was intentionally left unchanged.
10. Report any tests that were not run.

---

## 4. Core Architecture Rules

The following architecture rules are mandatory:

1. Strategies only produce `TradingDecision` objects.
2. Agents only produce `TradingDecision` objects.
3. Every `TradingDecision` must pass through the `RiskEngine`.
4. The `RiskEngine` produces a `RiskCheck`.
5. Only the Execution Module may create executable orders.
6. The Broker Module is the only module allowed to communicate with the Broker API.
7. The Market Data Module is the only module allowed to communicate with the Market Data Provider.
8. The Agent Module or LLM client abstraction is the only allowed access point to the LLM Provider.
9. API routes must not contain business logic.
10. Every execution must be represented by an `ExecutionStep`.

---

## 5. Safety Rules

The coding agent must never introduce support for:

- real-money trading
- live-trading endpoints
- short selling in Version 1
- margin trading in Version 1
- options trading in Version 1
- direct broker access from strategies or agents
- direct LLM execution of orders
- secrets in source code
- secrets in logs
- database schema changes without migrations

Version 1 is paper-trading and simulation only.

---

## 6. Implementation Behavior

Before editing, the coding agent should produce a short plan containing:

- task being implemented
- relevant documents used
- files likely to be changed
- tests likely to be added or updated
- potential risks

After editing, the coding agent should provide:

- summary of changed files
- behavior implemented
- tests run
- tests not run
- any documentation updates
- any unresolved issues

---

## 7. Prohibited Shortcuts

The coding agent must not:

- place business logic inside API route handlers
- call Alpaca directly from strategy or agent code
- bypass the Risk Engine
- create orders directly from LLM output
- silently change database schema
- silently change API response shapes
- remove audit logs
- remove `ExecutionStep` persistence
- hardcode secrets
- replace documented architecture with a simpler shortcut without approval

---

## 8. If Documentation and Code Conflict

If existing code conflicts with the documentation:

1. Identify the conflict.
2. Explain which document and code area disagree.
3. Do not silently choose one.
4. Ask for confirmation before changing architecture, schemas, or API contracts.

For small implementation-level inconsistencies, the agent may fix the code to match the accepted documentation if the task clearly allows it.
