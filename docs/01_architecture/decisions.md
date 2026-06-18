# Architecture Decisions

## 1. Purpose

This document provides an overview of the main architecture decisions for Trading Lab.

It acts as an index for Architecture Decision Records (ADRs) and summarizes the accepted architectural rules that must guide implementation.

The goal is to make important design decisions explicit so that developers and AI coding agents do not accidentally introduce architecture drift.

Detailed explanations are documented in individual ADR files under:

```text
/docs/01_architecture/02_adr/
```

---

## 2. Decision Index

| ADR | Title | Status | Summary |
|---|---|---|---|
| ADR-001 | Modular Monolith | Accepted | Trading Lab is implemented as a modular monolith, not as microservices. |
| ADR-002 | FastAPI Backend | Accepted | The backend is implemented with FastAPI and Python. |
| ADR-003 | PostgreSQL Database | Accepted | PostgreSQL is used as the primary persistent database. |
| ADR-004 | Agentic AI as Strategy | Accepted | Agentic AI is integrated as a strategy type and must follow the same decision pipeline as rule-based strategies. |
| ADR-005 | Risk Engine before Execution | Accepted | Every TradingDecision must pass through the Risk Engine before execution. |
| ADR-006 | REST API with Polling | Accepted | Frontend-backend communication uses REST; dashboard updates use polling in V1. |
| ADR-007 | Alpaca behind Adapters | Accepted | Alpaca integrations must be isolated behind Market Data and Broker adapters. |
| ADR-008 | ExecutionStep as Audit Unit | Accepted | Every strategy execution is represented as an ExecutionStep for auditability. |
| ADR-009 | Paper Trading Only in V1 | Accepted | Version 1 must not support real-money trading. |
| ADR-010 | PostgreSQL JSONB for Flexible Parameters | Accepted | Flexible strategy, agent, and log details may be stored in JSONB fields. |

---

## 3. Summary of Accepted Decisions

## 3.1 Modular Monolith

Trading Lab is implemented as a modular monolith.

The system is deployed as one backend application, but internally separated into clear modules:

- API Routes
- Experiment Module
- Scheduler Module
- Execution Module
- Strategy Module
- Agent Module
- Risk Module
- Market Data Module
- Broker Module
- Metrics Module
- Persistence Layer
- Domain Model

This reduces operational complexity while keeping the codebase modular and extensible.

Microservices are intentionally out of scope for Version 1.

---

## 3.2 FastAPI Backend

The backend is implemented with FastAPI and Python.

FastAPI is selected because Trading Lab needs strong support for:

- REST APIs
- AI and LLM integration
- trading/data workflows
- Python-based analytics
- fast iteration

The backend owns all business logic.

The frontend must not contain trading logic, risk logic, broker logic, or agent decision logic.

---

## 3.3 PostgreSQL Database

PostgreSQL is used as the main persistent database.

It stores:

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
- system event logs

PostgreSQL is preferred because the domain is relational and audit-heavy.

JSONB may be used for flexible data such as strategy parameters, agent inputs, parsed outputs, raw decision data, and event details.

---

## 3.4 Agentic AI as Strategy

Agentic AI is integrated as a strategy type.

This means that an agentic-AI strategy must behave like any other strategy from the perspective of the execution pipeline.

It must produce a standardized `TradingDecision`.

It must not execute orders directly.

The common flow remains:

```text
Strategy / Agent
→ TradingDecision
→ RiskCheck
→ ExecutionStep
→ Order / Trade, when applicable
```

This keeps rule-based strategies and agentic-AI strategies comparable and prevents the agent from bypassing system safety rules.

Historical Agentic-AI execution uses deterministic fake single-agent and
pipeline-agent providers only. Paper-trading Agentic AI is limited to
`AGENTIC_AI` + `SINGLE_AGENT` + `DAILY` + `SPY` and may call the ScaDS.AI
OpenAI-compatible API only through the Agent Module when explicitly enabled by
configuration. Agent pipeline paper trading, ORB/intraday agent paper trading,
tool calling, prompt editing, and direct agent access to broker, market-data,
scheduler, persistence, environment, or secret APIs remain out of scope.

---

## 3.5 Risk Engine before Execution

Every `TradingDecision` must pass through the Risk Engine before execution.

This applies to:

- Buy-and-Hold decisions
- Moving Average decisions
- Single-Agent decisions
- Pipeline-Agent decisions
- manual execution triggers
- scheduled historical execution triggers

The Risk Engine is authoritative.

Agents and strategies may suggest actions, but the Risk Engine determines the final executable action and size.

No order may be created without a `RiskCheck`.

BUY quantity is derived from available cash and whole-share rounding. SELL
liquidates the existing long SPY position and must never open a short position.

---

## 3.6 REST API with Polling

The Web Frontend communicates with the Backend API through REST.

Dashboard updates use polling in Version 1.

WebSockets or Server-Sent Events are intentionally not part of V1 because the expected execution frequency is daily, weekly, or monthly, not high-frequency or real-time trading.

This keeps frontend-backend communication simpler and sufficient for the initial system.

---

## 3.7 Alpaca behind Adapters

Alpaca is used in V1 for:

- market data
- paper trading

However, Alpaca-specific code must remain isolated behind adapter modules:

- `AlpacaMarketDataProvider`
- `AlpacaBrokerAdapter`

Strategies, agents, API routes, and frontend code must not call Alpaca directly.

This keeps the system replaceable if another market data provider or broker is added later.

---

## 3.8 ExecutionStep as Audit Unit

Every strategy or agent execution must be represented as an `ExecutionStep`.

An `ExecutionStep` is the central audit unit of the system.

It connects:

- market data snapshot
- trading decision
- risk check
- order
- trade
- portfolio snapshot
- metric snapshot
- agent logs
- system events

This allows every executed trade to be traced back to the data and decision that caused it.

---

## 3.9 Paper Trading Only in V1

Version 1 supports only internal simulation and paper trading.

Real-money trading is explicitly out of scope.

The system must not use live-trading endpoints.

The system must reject or block configurations that would route orders to real-money trading.

Current paper trading is intentionally controlled: supported SPY configurations
are `BUY_AND_HOLD` + `DAILY`, `MOVING_AVERAGE` + `DAILY`,
`OPENING_RANGE_BREAKOUT` + `INTRADAY_5_MIN`, gated diagnostics-only
`PAPER_TRADING_SMOKE_TEST` + `TEST_1_MIN`, and `AGENTIC_AI` +
`SINGLE_AGENT` + `DAILY` when ScaDS.AI is explicitly enabled. Broker
order-status polling exists for submitted paper orders. Full broker
reconciliation, outbox processing, account sync, position sync, and automatic
order cancellation remain deferred.

---

## 3.10 PostgreSQL JSONB for Flexible Parameters

Some parts of the system require flexible schema support.

Examples:

- strategy-specific parameters
- agent-specific configuration
- raw LLM outputs
- parsed LLM outputs
- event details
- broker sync details
- raw decision payloads

These may be stored in PostgreSQL JSONB fields.

However, core searchable and relational fields should remain explicit columns.

Example:

Use explicit columns for:

- experiment id
- strategy type
- status
- action
- timestamp
- symbol
- quantity
- price

Use JSONB for:

- strategy-specific optional parameters
- provider-specific response details
- agent prompt metadata
- raw diagnostic payloads

---

## 4. Architectural Rules

The following rules must be preserved during implementation.

## 4.1 System Boundaries

1. The frontend calls only the Backend API.
2. The frontend must not call Alpaca, the LLM provider, or the database directly.
3. The backend owns all business logic.
4. The database is accessed only through the backend.
5. External services are accessed only through dedicated modules or adapters.

---

## 4.2 Trading Pipeline Rules

1. Strategies only produce `TradingDecision`.
2. Agents only produce `TradingDecision`.
3. Every `TradingDecision` must pass through the Risk Engine.
4. The Risk Engine produces a `RiskCheck`.
5. The Execution Engine executes only approved or adjusted decisions.
6. HOLD decisions do not create executable orders.
7. Every execution step must be persisted.
8. Every executed trade must be auditable.

---

## 4.3 Broker and Market Data Rules

1. Market data access must go through the Market Data Module.
2. Broker access must go through the Broker Module.
3. Alpaca-specific logic must not leak into strategies or agents.
4. Paper-trading mode must use only paper-trading endpoints.
5. Paper trading may submit orders only through the Broker Module after a persisted, approved `RiskCheck`.
6. Broker sync may update submitted orders and fills, but full broker reconciliation, mismatch pause policy, account sync, position sync, and outbox processing are deferred.

---

## 4.4 Agentic AI Rules

1. LLM output must never be executed directly.
2. LLM output must be logged.
3. LLM output must be parsed.
4. LLM output must be validated.
5. Invalid LLM output must trigger a repair attempt.
6. If repair fails, the fallback action is HOLD.
7. Agent suggestions must still pass through the system Risk Engine.
8. The Agent Risk Manager inside a pipeline is not a replacement for the system Risk Engine.
9. Agents must not call broker, Alpaca, scheduler, persistence, repository, environment, or secret APIs directly.
10. Real LLM execution is currently limited to ScaDS.AI single-agent paper trading; historical agent execution remains deterministic fake-provider execution.

---

## 4.5 Persistence and Audit Rules

1. Every experiment must persist its configuration.
2. Every execution step must persist its input and output artifacts.
3. Every market data snapshot used for a decision must be stored.
4. Every trading decision must be stored.
5. Every risk check must be stored.
6. Every executed order and trade must be stored.
7. Every portfolio snapshot and metric snapshot must be stored.
8. Agent prompts, raw outputs, parsed outputs, and repair attempts must be stored for agentic-AI experiments.
9. Errors must be stored as system events.

---

## 5. Rules for Changing Architecture Decisions

Architecture decisions may be changed, but not silently.

A change requires an explicit update if it affects any of the following:

- system architecture
- module boundaries
- data model
- API contract
- execution pipeline
- Risk Engine behavior
- Broker integration
- Market Data integration
- Agentic AI workflow
- security or safety constraints

Before changing an accepted decision, the following must be documented:

1. Which decision is being changed.
2. Why the current decision is insufficient.
3. What alternatives were considered.
4. What the new decision is.
5. What risks or trade-offs the change introduces.
6. Which documents and code modules are affected.

If an AI coding agent detects that a task requires an architecture decision change, it must stop and request confirmation before implementing the change.

---

## 6. ADR Status Values

ADR files may use the following statuses:

- `Proposed`
- `Accepted`
- `Deprecated`
- `Superseded`

### Proposed

The decision is being considered but is not yet binding.

### Accepted

The decision is approved and must guide implementation.

### Deprecated

The decision should no longer be used for new work but may still describe existing legacy behavior.

### Superseded

The decision has been replaced by a newer ADR.

---

## 7. Related Documents

- `./system-overview.md`
- `./01_c4-model/c4-context.md`
- `./01_c4-model/c4-container.md`
- `./01_c4-model/c4-component.md`
- `./02_adr/ADR-001-modular-monolith.md`
- `./02_adr/ADR-002-fastapi-backend.md`
- `./02_adr/ADR-003-postgresql.md`
- `./02_adr/ADR-004-agent-as-strategy.md`
- `./02_adr/ADR-005-risk-engine-before-execution.md`
- `../02_domain/03_business-rules.md`
- `../05_backend/service-contracts.md`
