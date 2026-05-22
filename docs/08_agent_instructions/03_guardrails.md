# Agent Guardrails

## 1. Purpose

This document defines hard guardrails for AI coding agents working on Trading Lab.

These rules protect the system from unsafe trading behavior, architecture drift, secret leakage, broken auditability, and uncontrolled agentic-AI behavior.

If a requested implementation conflicts with these guardrails, the agent must stop and request confirmation.

---

## 2. Trading Safety Guardrails

The following rules are mandatory:

1. Version 1 must not support real-money trading.
2. Version 1 must not use live-trading endpoints.
3. Version 1 must only support simulation and paper trading.
4. Version 1 must only trade `SPY`.
5. Version 1 must not support short selling.
6. Version 1 must not support margin trading.
7. Version 1 must not support options trading.
8. Version 1 must not support high-frequency trading.
9. Broker integration must be paper-trading only.
10. Live endpoint configuration must be rejected or blocked.

---

## 3. Trading Pipeline Guardrails

The trading pipeline must not be bypassed.

Required pipeline:

```text
Strategy / Agent
→ TradingDecision
→ RiskEngine
→ RiskCheck
→ ExecutionEngine
→ Simulation or Paper Broker
```

Mandatory rules:

1. Strategies must never execute orders.
2. Agents must never execute orders.
3. LLM output must never be executed directly.
4. Every strategy or agent output must become a standardized `TradingDecision`.
5. Every `TradingDecision` must pass through the Risk Engine.
6. No order may be created without a `RiskCheck`.
7. HOLD decisions must not create executable orders.
8. Only the Execution Module may create executable orders.
9. Only the Broker Module may communicate with the Broker API.
10. Only the Market Data Module may communicate with the Market Data Provider.

---

## 4. Agentic-AI Guardrails

Agentic AI is allowed only within the documented decision pipeline.

Mandatory rules:

1. Agents may suggest an action.
2. Agents may suggest a position size if configured.
3. Agents may provide reasoning and confidence.
4. Agents may not override risk rules.
5. Agents may not call broker APIs.
6. Agents may not call market data APIs directly.
7. Agents may not write directly to database tables outside persistence abstractions.
8. Agent decisions must be logged.
9. Prompts must be logged.
10. Raw LLM outputs must be logged.
11. Parsed outputs must be logged.
12. Repair attempts must be logged.
13. If parsing and repair fail, fallback action is `HOLD`.

The Agent Risk Manager in a pipeline is not a substitute for the system Risk Engine.

---

## 5. Auditability Guardrails

Every execution must be auditable.

The system must preserve:

- `ExecutionStep`
- `MarketDataSnapshot`
- `TradingDecision`
- `RiskCheck`
- `Order`, if an order is created
- `Trade`, if an order is filled
- `PortfolioSnapshot`
- `MetricSnapshot`
- `AgentDecisionLog`, for agentic-AI experiments
- `BrokerSyncLog`, for broker synchronization
- `SystemEventLog`, for relevant events and errors

Do not remove or bypass these audit artifacts.

Every executed trade must be traceable back to:

```text
Experiment
→ ExecutionStep
→ MarketDataSnapshot
→ TradingDecision
→ RiskCheck
→ Order
→ Trade
```

---

## 6. Database Guardrails

Database changes require discipline.

Mandatory rules:

1. Any schema change requires an Alembic migration.
2. Any schema change requires updating `docs/03_database/schema.dbml`.
3. Any domain meaning change requires updating `docs/02_domain/01_entities.md`.
4. Enum values must not be renamed silently.
5. Existing audit tables must not be removed.
6. Foreign key relationships must preserve the audit chain.
7. `ExecutionStep` remains the central audit unit.
8. `RiskCheck` remains between `TradingDecision` and `Order`.

---

## 7. API Guardrails

API contracts must not change silently.

Mandatory rules:

1. Any endpoint change must update `docs/04_api/api-spec.md`.
2. Any OpenAPI change must update `docs/04_api/openapi.yaml`.
3. Response shapes must remain stable unless explicitly changed.
4. Error responses must use the documented error format.
5. Start and run-next-step operations remain asynchronous.
6. Large lists must support pagination.
7. Agent logs must be available through dedicated endpoints.

---

## 8. Security Guardrails

Mandatory rules:

1. Do not commit `.env`.
2. Do not hardcode API keys.
3. Do not log API keys.
4. Do not expose secrets to the frontend.
5. Do not return secrets from API endpoints.
6. Do not store secrets in agent prompts.
7. Do not store secrets in agent logs.
8. Use `.env.example` for documented configuration placeholders.

---

## 9. Architecture Guardrails

Mandatory rules:

1. The system remains a modular monolith in Version 1.
2. Do not introduce microservices without explicit architecture decision.
3. Do not introduce queues, Redis, Kafka, or separate workers unless explicitly requested.
4. API routes must not contain business logic.
5. Repositories must not contain business logic.
6. Frontend must not contain trading, risk, broker, or LLM logic.
7. Alpaca-specific code must stay behind adapters.
8. LLM-provider-specific code must stay behind an LLM client abstraction.
9. New dependencies must be justified and scoped.

V1 historical simulations must use FastAPI in-process background tasks, not an external queue or separate worker, unless a future design change is explicitly approved.

---

## 10. Stop Conditions

The agent must stop and request confirmation if a task requires:

- real-money trading support
- live-trading endpoint support
- direct broker calls from strategy or agent code
- bypassing Risk Engine
- changing database schema
- changing API contracts
- changing execution flow
- changing safety rules
- changing architecture style
- introducing a new external service
- adding authentication or multi-user support
- adding multi-asset trading
- adding short selling, margin, options, or high-frequency trading

Do not implement these changes without confirmation.
