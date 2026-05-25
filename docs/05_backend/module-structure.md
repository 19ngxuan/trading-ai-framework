# Backend Module Structure

## 1. Purpose

This document defines the internal module structure of the Trading Lab FastAPI backend.

The goal is to keep the backend modular, testable, and aligned with the architecture decisions documented in `/docs/01_architecture/`.

This document is especially important for developers and AI coding agents. It defines where code belongs, which modules may depend on each other, and which shortcuts are not allowed.

---

## 2. Backend Architecture Style

The backend is implemented as a modular monolith.

This means:

- The backend is deployed as one FastAPI application.
- The codebase is separated into clear internal modules.
- Modules communicate through explicit services and contracts.
- External systems are accessed only through dedicated adapter modules.
- Business logic must not be scattered across API routes, database repositories, or frontend code.

Microservices are not part of Version 1.

---

## 3. Recommended Backend Folder Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── errors.py
│   │   └── lifecycle.py
│   │
│   ├── api/
│   │   ├── routes/
│   │   │   ├── experiments.py
│   │   │   ├── execution_steps.py
│   │   │   ├── trades.py
│   │   │   ├── orders.py
│   │   │   ├── metrics.py
│   │   │   ├── agent_logs.py
│   │   │   ├── events.py
│   │   │   ├── comparison.py
│   │   │   └── options.py
│   │   └── schemas/
│   │       ├── experiment_schemas.py
│   │       ├── execution_schemas.py
│   │       ├── trade_schemas.py
│   │       ├── order_schemas.py
│   │       ├── metric_schemas.py
│   │       ├── agent_log_schemas.py
│   │       ├── event_schemas.py
│   │       ├── comparison_schemas.py
│   │       └── error_schemas.py
│   │
│   ├── domain/
│   │   ├── enums.py
│   │   ├── value_objects.py
│   │   └── interfaces.py
│   │
│   ├── modules/
│   │   ├── experiments/
│   │   ├── scheduler/
│   │   ├── execution/
│   │   ├── strategies/
│   │   ├── agents/
│   │   ├── risk/
│   │   ├── market_data/
│   │   ├── broker/
│   │   ├── metrics/
│   │   └── logging_events/
│   │
│   ├── persistence/
│   │   ├── database.py
│   │   ├── models/
│   │   └── repositories/
│   │
│   └── tests/
│
├── alembic/
├── alembic.ini
├── pyproject.toml
├── Dockerfile
└── .env.example
```

---

## 4. Top-Level Backend Areas

## 4.1 `core/`

The `core` package contains technical application infrastructure.

Typical files:

- `config.py`
- `logging.py`
- `errors.py`
- `lifecycle.py`

Responsibilities:

- environment configuration
- application settings
- logging setup
- exception mapping
- startup and shutdown lifecycle
- scheduler startup and shutdown wiring

Rules:

- `core` must not contain trading logic.
- `core` must not contain strategy logic.
- `core` must not contain database model definitions.

---

## 4.2 `api/`

The `api` package contains FastAPI routes and request/response schemas.

Responsibilities:

- define HTTP endpoints
- validate request data through Pydantic schemas
- map service results into response schemas
- return consistent error responses

Rules:

- API routes must not contain business logic.
- API routes must not call Alpaca directly.
- API routes must not call the LLM provider directly.
- API routes must not perform complex database queries directly.
- API routes should call application services in `modules/`.

Correct pattern:

```text
Route → Service → Repository
```

Incorrect pattern:

```text
Route → Database + Broker API + Strategy Logic
```

---

## 4.3 `domain/`

The `domain` package contains shared domain concepts.

Responsibilities:

- enums
- value objects
- domain DTOs
- interface definitions
- stable domain contracts

Examples:

- `ExperimentStatus`
- `ExperimentMode`
- `StrategyType`
- `TradingFrequency`
- `Action`
- `OrderStatus`
- `ExecutionStepStatus`
- `TriggerType`
- `AgentMode`
- `TradingDecisionData`
- `RiskCheckResult`
- `PortfolioState`
- `StrategyContext`

Rules:

- Domain concepts must be reusable across modules.
- Domain objects must not depend on infrastructure modules.
- Domain objects must not call database, broker, market data, or LLM APIs.

---

## 4.4 `modules/`

The `modules` package contains the main business modules of the backend.

Each module should have a clear responsibility and should expose services or interfaces to other modules.

Modules:

- `experiments`
- `scheduler`
- `execution`
- `strategies`
- `agents`
- `risk`
- `market_data`
- `broker`
- `metrics`
- `logging_events`

---

## 4.5 `persistence/`

The `persistence` package contains database infrastructure.

Responsibilities:

- SQLAlchemy models
- database session management
- repositories
- persistence-specific mapping

Rules:

- Business logic must not be implemented in repositories.
- Repositories should encapsulate database access.
- Services should not scatter raw ORM queries throughout the codebase.
- Database schema changes require Alembic migrations.
- Database schema changes require updates to `/docs/03_database/schema.dbml`.

---

## 5. Business Modules

## 5.1 Experiment Module

Suggested path:

```text
backend/app/modules/experiments/
├── service.py
├── validators.py
└── status_machine.py
```

Responsibilities:

- create experiments
- validate experiment configuration
- initialize strategy configuration
- initialize portfolio state
- manage experiment status transitions
- start, pause, resume, stop, complete, and fail experiments

Allowed dependencies:

- Domain Model
- Persistence Layer
- Execution Module for starting execution flows
- Scheduler Module for scheduling running experiments, if needed

Not allowed:

- direct broker API calls
- direct LLM calls
- direct market data provider calls
- strategy decision logic
- risk validation logic

Key rules:

- Invalid status transitions must be rejected.
- `start` is valid only from `CREATED`. `resume` is valid only from `PAUSED`.
- Completed or stopped experiments must not be restarted in Version 1.
- Experiment creation must create an initial portfolio.

---

## 5.2 Scheduler Module

Suggested path:

```text
backend/app/modules/scheduler/
├── scheduler.py
└── jobs.py
```

Responsibilities:

- configure APScheduler
- find running experiments that are due for execution
- trigger scheduled execution steps
- support manual run-next-step execution
- prevent concurrent execution for the same experiment

Allowed dependencies:

- Experiment Module
- Execution Module
- Persistence Layer

Not allowed:

- strategy logic
- risk logic
- broker-specific logic
- LLM-specific logic

Key rules:

- Scheduled and manual execution must use the same execution pipeline.
- The scheduler must not depend on the frontend.
- A single experiment must not run two execution steps concurrently.
- Historical simulation background execution in V1 uses FastAPI in-process background tasks. APScheduler handles due scheduled runs, but no external queue or separate worker service is introduced.

---

## 5.3 Execution Module

Suggested path:

```text
backend/app/modules/execution/
├── orchestrator.py
├── engine.py
├── simulation_provider.py
└── paper_provider.py
```

Responsibilities:

- create and run execution steps
- coordinate market data loading
- coordinate strategy or agent decision generation
- coordinate risk checks
- execute approved decisions
- update portfolio state
- store portfolio snapshots
- trigger metric calculation
- store system events

Allowed dependencies:

- Domain Model
- Persistence Layer
- Market Data Module
- Strategy Module
- Agent Module
- Risk Module
- Broker Module
- Metrics Module
- Logging Events Module

Key rules:

- The Execution Module coordinates the execution pipeline.
- The Execution Module is the only module that creates executable orders.
- The Execution Module must persist each `ExecutionStep`.
- The Execution Module must not bypass the Risk Module.
- An execution step may create zero or one Order. An Order may create zero, one, or many Trade records.

Core flow:

```text
Experiment
→ ExecutionStep
→ MarketDataSnapshot
→ TradingDecision
→ RiskCheck
→ Order / Trade
→ PortfolioSnapshot
→ MetricSnapshot
→ SystemEventLog
```

---

## 5.4 Strategy Module

Suggested path:

```text
backend/app/modules/strategies/
├── base.py
├── factory.py
├── buy_and_hold.py
├── moving_average.py
└── agentic_ai_strategy.py
```

Responsibilities:

- define the strategy interface
- select strategies through a factory
- implement rule-based strategies
- wrap Agentic AI as a strategy type
- produce standardized trading decisions

Allowed dependencies:

- Domain Model
- Agent Module only through `AgenticAIStrategy`

Not allowed:

- direct broker access
- direct market data provider access
- direct LLM provider access, except through Agent Module
- direct order execution
- direct database persistence

Key rules:

- Strategies only decide.
- Strategies return `TradingDecision` data.
- Strategies do not execute orders.
- Strategies do not bypass the Risk Module.

---

## 5.5 Agent Module

Suggested path:

```text
backend/app/modules/agents/
├── engine.py
├── prompt_builder.py
├── output_parser.py
├── repair.py
├── llm_client.py
├── single_agent.py
└── pipeline_agent.py
```

Responsibilities:

- build agent inputs
- build prompts
- call the LLM provider
- parse LLM outputs
- validate structured outputs
- run repair prompts when output is invalid
- create agent decision logs
- produce standardized trading decisions

Allowed dependencies:

- Domain Model
- Persistence Layer for agent logs
- Deterministic fake agent providers in the current implementation
- Future LLM Provider through an explicit adapter/client only after a separate safety milestone

Not allowed:

- direct broker access
- direct order execution
- direct market data provider access
- bypassing the Risk Module

Key rules:

- LLM output must never be executed directly.
- LLM output must be logged, parsed, and validated.
- If repair fails, fallback action is `HOLD`.
- The system Risk Module remains mandatory even if the agent pipeline includes an Agent Risk Manager.
- Current M10/M11 agent execution is historical manual-step only. Paper-trading
  and scheduler-triggered agent execution are not implemented.

---

## 5.6 Risk Module

Suggested path:

```text
backend/app/modules/risk/
├── engine.py
├── rules.py
└── position_sizing.py
```

Responsibilities:

- validate every `TradingDecision`
- enforce safety rules
- determine final executable action
- determine final quantity or notional
- reject or adjust unsafe decisions
- produce `RiskCheck`

Allowed dependencies:

- Domain Model
- Persistence Layer for recent trades and metrics, if required

Not allowed:

- broker API calls
- LLM calls
- market data provider calls
- order execution

Key rules:

- No decision may be executed without a `RiskCheck`.
- The Risk Module is authoritative over agent suggestions.
- Agents may suggest position size, but Risk Module decides final executable size.
- V1 receives risk configuration from `strategy_configs.parameters_json.riskConfig` after applying documented defaults.
- M13 position sizing receives `position_sizing_type` from `strategy_configs` and
  optional `positionSizingValue` from `strategy_configs.parameters_json`.

---

## 5.7 Market Data Module

Suggested path:

```text
backend/app/modules/market_data/
├── provider.py
├── alpaca_provider.py
├── indicators.py
└── mapper.py
```

Responsibilities:

- fetch SPY market data
- fetch historical data
- fetch latest data
- compute or prepare indicator values
- create market data snapshots
- handle missing market data

Allowed dependencies:

- Domain Model
- Persistence Layer
- external Market Data Provider through adapter implementation

Not allowed:

- broker API calls
- LLM calls
- order execution
- strategy decision logic

Key rules:

- Market data access must be isolated in this module.
- Market data used for a decision must be persisted as `MarketDataSnapshot`.
- Strategies and agents receive market data through context, not by calling providers directly.

---

## 5.8 Broker Module

Suggested path:

```text
backend/app/modules/broker/
├── broker_adapter.py
├── alpaca_broker_adapter.py
└── sync_service.py
```

Responsibilities:

- encapsulate Alpaca Paper Trading integration
- submit paper orders
- read account state
- read positions
- read order status
- synchronize broker state with local state
- create broker sync logs
- detect broker-state mismatches

Allowed dependencies:

- Domain Model
- Persistence Layer
- external Broker API through adapter implementation

Not allowed:

- strategy decision logic
- agent decision logic
- direct frontend access

Key rules:

- Only paper-trading endpoints may be used in Version 1.
- Live-trading endpoints must be blocked.
- In paper-trading mode, broker state is the source of truth.
- If local and broker state diverge, the experiment must be paused and a broker sync event must be recorded.

---

## 5.9 Metrics Module

Suggested path:

```text
backend/app/modules/metrics/
├── calculator.py
└── benchmark_service.py
```

Responsibilities:

- calculate total return
- calculate profit/loss
- count trades
- calculate max drawdown
- calculate Buy-and-Hold comparison
- produce metric snapshots

Allowed dependencies:

- Domain Model
- Persistence Layer

Not allowed:

- broker API calls
- LLM calls
- order execution
- market data provider calls directly

Key rules:

- Metrics must be updated after each execution step.
- Metrics must be reproducible from stored trades and portfolio snapshots.
- Buy-and-Hold benchmark should be represented as its own experiment.

---

## 5.10 Logging Events Module

Suggested path:

```text
backend/app/modules/logging_events/
├── event_service.py
└── event_types.py
```

Responsibilities:

- create system event logs
- standardize event types
- log important domain and infrastructure events
- support filtering by level and event type

Examples of events:

- `EXPERIMENT_CREATED`
- `EXPERIMENT_STARTED`
- `MARKET_DATA_MISSING`
- `STRATEGY_DECISION_CREATED`
- `RISK_LIMIT_TRIGGERED`
- `ORDER_SUBMITTED`
- `ORDER_FILLED`
- `ORDER_FAILED`
- `BROKER_SYNC_FAILED`
- `BROKER_STATE_MISMATCH`
- `LLM_OUTPUT_INVALID`
- `LLM_REPAIR_ATTEMPTED`
- `FALLBACK_HOLD_USED`

---

## 6. Persistence Structure

Suggested path:

```text
backend/app/persistence/
├── database.py
├── models/
│   ├── experiment_model.py
│   ├── strategy_config_model.py
│   ├── portfolio_model.py
│   ├── execution_step_model.py
│   ├── market_data_snapshot_model.py
│   ├── trading_decision_model.py
│   ├── risk_check_model.py
│   ├── order_model.py
│   ├── trade_model.py
│   ├── portfolio_snapshot_model.py
│   ├── metric_snapshot_model.py
│   ├── agent_decision_log_model.py
│   ├── broker_sync_log_model.py
│   └── system_event_log_model.py
│
└── repositories/
    ├── experiment_repository.py
    ├── strategy_config_repository.py
    ├── portfolio_repository.py
    ├── execution_step_repository.py
    ├── market_data_repository.py
    ├── decision_repository.py
    ├── risk_check_repository.py
    ├── order_repository.py
    ├── trade_repository.py
    ├── portfolio_snapshot_repository.py
    ├── metric_repository.py
    ├── agent_log_repository.py
    ├── broker_sync_repository.py
    └── event_repository.py
```

Rules:

- SQLAlchemy models represent database tables.
- Repositories encapsulate database access.
- Business logic belongs in services, not repositories.
- Schema changes require Alembic migrations.
- Schema changes require updates to `/docs/03_database/schema.dbml`.

---

## 7. Allowed Dependency Direction

Preferred dependency direction:

```text
API Routes
→ Application Services / Modules
→ Domain Model
→ Persistence Layer
→ Database
```

External provider access:

```text
Market Data Module → Market Data Provider
Broker Module → Broker API
Agent Module → LLM Provider
```

Execution pipeline:

```text
Execution Module
→ Market Data Module
→ Strategy Module / Agent Module
→ Risk Module
→ Execution Provider / Broker Module
→ Metrics Module
→ Persistence Layer
```

---

## 8. Forbidden Dependencies

The following dependencies are not allowed:

```text
Frontend → Database
Frontend → Alpaca
Frontend → LLM Provider
Frontend → Broker API

Strategy Module → Broker API
Strategy Module → Broker Module
Strategy Module → Database directly
Strategy Module → Execution Module

Agent Module → Broker API
Agent Module → Broker Module
Agent Module → Execution Module
Agent Module → Market Data Provider directly

API Routes → Broker API
API Routes → LLM Provider
API Routes → complex business logic

Repository → business decision logic
```

---

## 9. Critical Backend Rules

1. API routes contain no business logic.
2. Strategies produce only `TradingDecision` objects.
3. Agents produce only `TradingDecision` objects.
4. Every `TradingDecision` must pass through the Risk Module.
5. The Risk Module produces a `RiskCheck`.
6. Only the Execution Module can create executable orders.
7. Only the Broker Module can communicate with the Broker API.
8. Only the Market Data Module can communicate with the Market Data Provider.
9. Only the Agent Module or LLM client abstraction can communicate with the LLM Provider.
10. Every execution must be represented as an `ExecutionStep`.
11. Every executed trade must be auditable.
12. Version 1 must not support real-money trading.

---

## 10. Related Documents

- `../01_architecture/system-overview.md`
- `../01_architecture/01_c4-model/c4-component.md`
- `../01_architecture/decisions.md`
- `./service-contracts.md`
- `../02_domain/01_entities.md`
- `../02_domain/02_workflows.md`
- `../02_domain/03_business-rules.md`
- `../04_api/api-spec.md`
- `../03_database/schema.dbml`
