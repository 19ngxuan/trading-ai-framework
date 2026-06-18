# System Overview

## 1. Purpose

This document provides a high-level overview of the Trading Lab system architecture.

The goal is to describe the system's purpose, main components, execution flow, architectural boundaries, and key design principles. It is intended for developers and AI coding agents working on the codebase.

This document is not a detailed API specification, database schema, or implementation guide. Those details are documented separately.


## 2. Product Summary

Trading Lab is a web-based strategy and agentic-AI trading experimentation platform for SPY paper trading.

The system allows users to create trading experiments, run rule-based or AI-based strategies, simulate or execute paper trades, track portfolio performance, and compare strategies against a Buy-and-Hold benchmark.

The primary goal is not to provide financial advice or live trading automation. The system is designed as a research and experimentation platform for evaluating trading strategies and agentic-AI decision loops under controlled conditions.



## 3. Scope of Version 1

Version 1 focuses on a single asset: SPY.

V1 is split into three implementation stages:

### V1a: Internal Simulation

- Create experiments.
- Run historical simulations.
- Support Buy-and-Hold strategy.
- Support 200-day Moving Average strategy.
- Maintain a virtual portfolio per experiment.
- Store execution steps, decisions, trades, portfolio snapshots, and metrics.
- Compare strategy performance against Buy and Hold.

### V1b: Paper Trading

- Integrate Alpaca Paper Trading.
- Use Alpaca Market Data.
- Place paper orders through Alpaca.
- Synchronize broker state with local state.
- Treat the broker as the source of truth in paper-trading mode.

### V1c: Agentic AI

- Add Agentic AI as a strategy type.
- Support a Single-Agent decision mode.
- Support a simple Pipeline-Agent mode.
- Support ScaDS.AI single-agent decisions for controlled daily SPY paper trading when explicitly enabled.
- Store agent inputs, prompts, raw outputs, parsed outputs, decisions, and risk checks.
- Compare agentic strategies against rule-based baselines.


## 4. High-Level Architecture

The system is implemented as a modular monolith.

It consists of:

- React frontend
- FastAPI backend
- PostgreSQL database
- Integrated backend scheduler
- Alpaca Market Data integration
- Alpaca Paper Trading integration
- LLM provider integration for agentic-AI strategies

The frontend communicates with the backend through REST APIs. Dashboard data is refreshed through polling.

V1 historical simulations run inside the FastAPI backend using in-process background tasks. No external queue, Redis, Celery, or separate worker service is used in V1. The frontend observes progress by polling REST endpoints.

The backend owns all business logic. The frontend must not contain trading logic, risk logic, broker integration, or agent decision logic.

## 5. Main Components

### Frontend

The frontend provides the user interface for creating experiments, monitoring running experiments, viewing charts, comparing strategies, and inspecting agent decision logs.

### Backend API

The backend exposes REST endpoints for experiment management, execution steps, metrics, trades, orders, agent logs, events, and comparison views.

### Experiment Service

The Experiment Service manages experiment creation, validation, status transitions, and portfolio initialization.

### Scheduler

The Scheduler triggers execution steps for running experiments according to their configured trading frequency. It also supports manual step execution.

### Execution Orchestrator

The Execution Orchestrator runs one execution step at a time. It coordinates market data loading, strategy execution, risk checks, order execution, portfolio updates, metrics calculation, and logging.

### Market Data Module

The Market Data Module provides SPY market data. In V1, Alpaca is the primary external data provider.

### Strategy Module

The Strategy Module executes rule-based strategies and returns standardized trading decisions.

### Agent Module

The Agent Module supports agentic-AI strategies. It builds prompts, calls the LLM provider, parses outputs, performs repair attempts if needed, and stores agent logs.

### Risk Module

The Risk Module validates every trading decision before execution. It enforces risk and safety rules.

### Execution Module

The Execution Module executes approved decisions either through internal simulation or Alpaca Paper Trading.

### Broker Module

The Broker Module encapsulates Alpaca Paper Trading integration and broker-state synchronization.

### Metrics Module

The Metrics Module calculates return, profit/loss, number of trades, max drawdown, and benchmark comparison metrics.

Benchmark experiments are normal experiments with `strategy_type = BUY_AND_HOLD`. Metric snapshots may store denormalized benchmark comparison fields for fast display.

### Persistence Layer

The Persistence Layer stores all experiments, execution steps, decisions, orders, trades, snapshots, metrics, logs, and events in PostgreSQL.

## 6. Core Execution Flow

The core execution flow is:

1. Load experiment configuration.
2. Create an ExecutionStep.
3. Load market data.
4. Store a MarketDataSnapshot.
5. Load current portfolio state.
6. Build a StrategyContext.
7. Run the selected strategy or agent.
8. Store the TradingDecision.
9. Run the RiskEngine.
10. Store the RiskCheck.
11. If the final action is HOLD, skip order execution.
12. Otherwise, execute the order through simulation or Alpaca Paper Trading.
13. Store an Order if applicable, and zero or more Trade records when fills occur.
14. Update the portfolio.
15. Store a PortfolioSnapshot.
16. Calculate metrics.
17. Store a MetricSnapshot.
18. Store relevant SystemEventLogs.
19. Mark the ExecutionStep as completed, skipped, or failed.

## 7. Key Architectural Principles

### Strategies and agents only produce TradingDecisions

Strategies and agents must never execute orders directly. They only produce standardized TradingDecision objects.

### RiskEngine is mandatory

Every TradingDecision must pass through the RiskEngine before execution.

### Execution is centralized

Orders are executed only through the Execution Module. Depending on the experiment mode, execution is delegated to either the simulation provider or the Alpaca paper-trading provider.

### Broker access is isolated

Alpaca-specific logic must remain inside the Broker Module and Market Data Module. Strategy and agent code must not call Alpaca directly.

### Agentic AI is a strategy type

Agentic AI is integrated as a strategy type. It must follow the same decision-risk-execution pipeline as rule-based strategies.

### Every decision must be auditable

Every executed trade must be traceable to:

- Experiment
- ExecutionStep
- MarketDataSnapshot
- TradingDecision
- RiskCheck
- Order
- Trade
- PortfolioSnapshot
- MetricSnapshot

### Paper trading only

Version 1 must not support real-money trading.

## 8. External Systems

### Alpaca Market Data

Used to retrieve SPY market data.

### Alpaca Paper Trading

Used to place paper-trading orders in V1b.

The system must only use Alpaca paper-trading endpoints in V1.

### LLM Provider

Used by the Agent Module to generate agentic-AI trading decisions.

Historical agent execution uses deterministic fake providers. ScaDS.AI is
available only for `PAPER_TRADING` + `AGENTIC_AI` + `SINGLE_AGENT` + `DAILY` +
`SPY` when explicitly configured. LLM outputs must be parsed, validated, stored
as TradingDecision input, and passed through the RiskEngine before execution.
Agents must not access broker, Alpaca, persistence, scheduler, environment, or
secret APIs directly.

## 9. Out of Scope

The following features are out of scope for Version 1:

- Real-money trading
- Live-trading endpoints
- Mobile app
- User registration
- Multi-user support
- Trading individual S&P 500 stocks
- Multi-asset portfolio management
- Short selling
- Margin trading
- Options trading
- High-frequency trading
- Reinforcement learning
- Tax reporting
- Public financial advice

## 10. References

Related documents:

- `/docs/01_architecture/01_c4-model/c4-context.md`
- `/docs/01_architecture/01_c4-model/c4-container.md`
- `/docs/01_architecture/01_c4-model/c4-component.md`
- `/docs/01_architecture/decisions.md`
- `/docs/02_domain/01_entities.md`
- `/docs/02_domain/02_workflows.md`
- `/docs/02_domain/03_business-rules.md`
- `/docs/05_backend/service-contracts.md`
- `/docs/04_api/api-spec.md`
- `/docs/03_database/schema.dbml`
