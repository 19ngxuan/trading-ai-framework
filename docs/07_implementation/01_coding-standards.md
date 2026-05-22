# Coding Standards

## 1. Purpose

This document defines implementation standards for Trading Lab.

The goal is to keep the codebase consistent, modular, testable, and aligned with the architecture and domain documentation.

These standards apply to all backend, frontend, database, and integration code.

---

## 2. General Rules

- Keep implementation aligned with the architecture documents.
- Do not introduce new modules, services, tables, or API contracts without checking the relevant docs.
- Prefer clear, explicit code over clever abstractions.
- Keep business logic out of API routes and UI components.
- Keep external provider code isolated behind adapters.
- Do not bypass the execution pipeline.
- Do not commit secrets.
- Do not log API keys or credentials.

---

## 3. Backend Standards

Backend code is implemented with FastAPI and Python.

### Layering

Use the following layering:

```text
API Route -> Service / Module -> Repository -> Database
```

API routes should:

- validate requests
- call application services
- map responses
- return HTTP status codes

API routes must not:

- implement trading logic
- calculate portfolio metrics
- call Alpaca directly
- call LLM providers directly
- write complex SQL directly

### Module Boundaries

Backend modules must preserve their responsibilities:

- `experiments`: experiment lifecycle and status transitions
- `scheduler`: scheduled and manual execution triggers
- `execution`: execution-step orchestration and execution providers
- `strategies`: rule-based and agentic strategy wrappers
- `agents`: LLM orchestration and agent logs
- `risk`: risk validation and final executable action
- `market_data`: market data providers and snapshots
- `broker`: broker adapters and synchronization
- `metrics`: performance metric calculation
- `persistence`: SQLAlchemy models, repositories, migrations

---

## 4. Core Pipeline Rule

The following pipeline must not be bypassed:

```text
Strategy / Agent
-> TradingDecision
-> RiskEngine
-> RiskCheck
-> ExecutionEngine
-> Order / Trade
```

Strategies and agents must not execute orders directly.

Every `TradingDecision` must pass through the Risk Engine before execution.

---

## 5. Persistence Standards

- Use SQLAlchemy models for database mapping.
- Use repositories to encapsulate database access.
- Use Alembic for schema migrations.
- Every model change requires a migration.
- Every schema change requires an update to `docs/03_database/schema.dbml`.
- Every domain meaning change requires an update to `docs/02_domain/01_entities.md`.

Repositories should not contain business logic.

---

## 6. Error Handling

Use explicit domain/application exceptions where possible.

API errors should follow the documented format:

```json
{
  "errorCode": "INVALID_EXPERIMENT_STATUS",
  "message": "Experiment cannot be started because it is already running.",
  "details": {}
}
```

Do not expose internal stack traces through API responses.

---

## 7. Logging Standards

Important events must be written as `SystemEventLog` records when relevant.

Log at least:

- experiment created, started, paused, stopped, completed, failed
- market data missing
- strategy decision created
- risk limit triggered
- order submitted, filled, failed
- broker sync failed or mismatched
- LLM output invalid
- repair attempted
- fallback HOLD used

Agentic-AI experiments must store:

- input JSON
- prompt text
- raw output
- parsed output
- parsing status
- repair prompt and repair output when used

---

## 8. Frontend Standards

Frontend code is implemented with React and TypeScript.

### Rules

- Keep trading logic out of frontend components.
- Use API clients and hooks for backend communication.
- Use TanStack Query for fetching, caching, mutations, and polling.
- Use typed API response models.
- Keep pages thin and move reusable UI into components.
- Keep feature-specific logic inside `features/`.

### UI Rules

- Dashboard and comparison screens should be visually clear and polished.
- Detail screens and agent logs should remain technically inspectable.
- JSON payloads should be shown in readable viewers or expandable panels.
- Error states must be visible to the user.

---

## 9. Testing Standards

Backend tests should prioritize:

- Risk Engine
- Metrics Engine
- Execution Orchestrator
- Portfolio updates
- Agent Output Parser
- Experiment status transitions

Frontend tests should prioritize:

- ExperimentTable
- CreateExperimentForm
- ExperimentActions
- AgentLogAccordion
- EventTable

External Alpaca and LLM calls must be mocked in normal tests.

---

## 10. Forbidden Shortcuts

Do not:

- call Alpaca directly from strategies or agents
- call LLM providers directly from API routes
- execute orders from agent code
- skip the Risk Engine
- store secrets in code
- expose secrets in UI
- remove audit logs for convenience
- merge Order and Trade for paper-trading implementation
- introduce real-money trading in Version 1
