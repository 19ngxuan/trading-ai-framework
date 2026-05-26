# Domain Workflows

## 1. Purpose

This document describes the main domain workflows of Trading Lab.

It explains how experiments move through the system and how domain entities interact during simulation, paper trading, agentic-AI decisions, risk checks, metrics calculation, and error handling.

This document is intended for developers and AI coding agents. It should be used together with `entities.md` and `business-rules.md`.

---

## 2. Workflow Overview

The most important workflow is the execution of an experiment step.

The canonical flow is:

```text
Experiment
→ ExecutionStep
→ MarketDataSnapshot
→ TradingDecision
→ RiskCheck
→ Order
→ Trade
→ PortfolioSnapshot
→ MetricSnapshot
→ SystemEventLog
```

For agentic-AI experiments:

```text
Experiment
→ ExecutionStep
→ MarketDataSnapshot
→ AgentDecisionLog[]
→ TradingDecision
→ RiskCheck
→ Order / Trade
→ PortfolioSnapshot
→ MetricSnapshot
```

Every workflow must preserve auditability.

---

## 3. Experiment Lifecycle Workflow

## 3.1 Create Experiment

Goal:

Create a new experiment with configuration, strategy settings, and an initial portfolio.

Flow:

1. User submits experiment configuration through the frontend.
2. Backend validates required fields.
3. Backend validates that `asset_symbol` is supported in Version 1.
4. Backend creates an `Experiment` with status `CREATED`.
5. Backend creates one `StrategyConfig` for the experiment.
6. Backend creates one `Portfolio` initialized with `initial_capital` as cash.
7. Backend stores a `SystemEventLog` with `EXPERIMENT_CREATED`.
8. Backend returns the created experiment and portfolio.

Result:

- Experiment exists.
- Experiment status is `CREATED`.
- Initial portfolio exists.
- No execution step has run yet.

---

## 3.2 Start Experiment

Goal:

Move an experiment from `CREATED` to `RUNNING`.

Flow:

1. User starts the experiment.
2. Backend validates the current experiment status.
3. Backend changes status to `RUNNING`.
4. Backend stores `EXPERIMENT_STARTED` event.
5. Backend schedules or triggers execution depending on experiment mode.

Allowed transitions:

```text
CREATED → RUNNING
```

Paused experiments must use the Resume Experiment workflow. `start` must reject `PAUSED`.

Invalid transitions must be rejected.

---

## 3.3 Pause Experiment

Goal:

Temporarily stop execution without finalizing the experiment.

Flow:

1. User pauses a running experiment.
2. Backend validates that status is `RUNNING`.
3. Backend changes status to `PAUSED`.
4. Scheduler stops triggering new steps for that experiment.
5. Backend stores `EXPERIMENT_PAUSED` event.

Allowed transition:

```text
RUNNING → PAUSED
```

---

## 3.4 Stop Experiment

Goal:

End an experiment permanently.

Flow:

1. User stops an experiment.
2. Backend validates that the experiment is stoppable.
3. Backend changes status to `STOPPED`.
4. Backend stores `EXPERIMENT_STOPPED` event.
5. Scheduler must no longer trigger execution steps for that experiment.

Allowed transitions:

```text
RUNNING → STOPPED
PAUSED → STOPPED
```

---

## 3.5 Complete Experiment

Goal:

Mark a historical simulation as finished.

Flow:

1. Historical execution reaches the configured `end_date`.
2. Backend calculates final metrics.
3. Backend changes experiment status to `COMPLETED`.
4. Backend stores `EXPERIMENT_COMPLETED` event.

Allowed transition:

```text
RUNNING → COMPLETED
```

---

## 4. Historical Simulation Workflow

Goal:

Run an experiment over historical market data from `start_date` to `end_date`.

Flow:

1. Experiment is started.
2. Backend loads historical market data for SPY.
3. Backend iterates through the data according to `trading_frequency`.
4. For each selected timestamp, backend creates an `ExecutionStep` with `trigger_type = HISTORICAL`.
5. Backend loads or derives market data and indicators.
6. Backend stores a `MarketDataSnapshot`.
7. Backend runs the configured strategy.
8. Strategy returns a `TradingDecision`.
9. Backend stores the `TradingDecision`.
10. Backend passes the decision to the Risk Engine.
11. Backend stores the `RiskCheck`.
12. If final action is `HOLD`, no order is created.
13. If final action is `BUY` or `SELL`, backend creates a simulated order.
14. Simulated execution creates a `Trade` if the order is filled.
15. Backend updates `Portfolio`.
16. Backend stores `PortfolioSnapshot`.
17. Backend calculates and stores `MetricSnapshot`.
18. Backend marks the `ExecutionStep` as `COMPLETED`, `SKIPPED`, or `FAILED`.
19. After all steps are processed, backend marks the experiment as `COMPLETED`.

Important rules:

- V1 historical simulations are submitted via FastAPI and executed as in-process background tasks. The frontend tracks progress through polling. No external queue or worker service is used in V1.
- Historical simulation must be reproducible from stored data and configuration.
- Every step must be auditable.
- Missing market data should result in a skipped step and a system event.

---

## 5. Live-Like Simulation Workflow

Goal:

Run a simulation over time using scheduled execution steps.

Flow:

1. Experiment is created with `mode = LIVE_SIMULATION`.
2. User starts the experiment.
3. Experiment status becomes `RUNNING`.
4. Scheduler identifies the next due execution time.
5. Scheduler triggers an `ExecutionStep` with `trigger_type = SCHEDULED`.
6. Backend fetches latest market data.
7. Backend runs the same decision-risk-execution pipeline as historical simulation.
8. Backend stores snapshots, metrics, and events.
9. Scheduler waits until the next due time.

Manual debug execution:

- User may trigger `run-next-step`.
- This creates an `ExecutionStep` with `trigger_type = MANUAL`.
- The same execution pipeline must be used.

Important rule:

Manual and scheduled execution must not use different business logic.

---

## 6. Paper Trading Workflow

Goal:

Run a supported rule-based strategy using Alpaca Paper Trading instead of
internal simulated execution. The current implementation supports SPY
Buy-and-Hold daily paper trading, SPY Moving Average daily paper trading, and
scheduled SPY Opening Range Breakout five-minute paper trading.

Flow:

1. Experiment is created with `mode = PAPER_TRADING`.
2. User starts the experiment. `/start` changes lifecycle status only and must not submit an order.
3. Backend validates that only paper-trading endpoints are configured.
4. Manual `run-next-step` or the paper-trading scheduler creates an `ExecutionStep`.
5. Backend fetches market data.
6. Backend stores `MarketDataSnapshot`.
7. Backend runs the supported rule-based strategy.
8. Backend stores `TradingDecision`.
9. Backend runs Risk Engine.
10. Backend stores `RiskCheck`.
11. If final action is `HOLD`, no broker order is submitted.
12. If final action is `BUY` or `SELL`, Execution Module calls Broker Module.
13. Broker Module submits a paper order through Alpaca.
14. Backend stores `Order`.
15. If the immediate broker response reports filled quantity, backend stores `Trade`.
16. Backend updates local portfolio only for filled quantity.
17. Backend stores `PortfolioSnapshot` and `MetricSnapshot`.
18. A separate broker-sync job polls submitted paper orders until terminal broker
    status. Newly confirmed fill quantity creates additional `Trade` records and
    updates the local portfolio by the fill delta only.

Important rules:

- Broker API must only be accessed through the Broker Module.
- Paper trading must not use live-trading endpoints.
- Paper scheduler execution is disabled by default and supports Buy-and-Hold
  daily SPY, Moving Average daily SPY, Opening Range Breakout intraday SPY, and
  gated smoke-test SPY experiments.
- Manual paper `run-next-step` supports Buy-and-Hold and Moving Average
  debugging. Opening Range Breakout paper trading is scheduled-only in M23.
- ORB paper scheduling evaluates completed regular-session 5-minute bars only.
  Missing expected completed bars are skipped before step creation.
- Broker order-status polling is implemented for submitted paper orders.
- Full broker reconciliation, account sync, position sync, outbox processing, and automatic order cancellation are deferred.
- Agentic-AI paper trading is not implemented.

---

## 7. Strategy Decision Workflow

Goal:

Convert strategy logic into a standardized `TradingDecision`.

Flow:

1. Execution Module builds strategy context.
2. Strategy receives:
   - experiment configuration
   - strategy configuration
   - market data snapshot
   - current portfolio state
   - previous trades
   - current metrics
   - execution timestamp
3. Strategy evaluates its rules.
4. Strategy returns a standardized `TradingDecision`.
5. Backend stores the decision.
6. Backend passes the decision to the Risk Engine.

Supported V1 strategies:

- Buy and Hold
- Moving Average
- Agentic AI strategy wrapper

Important rules:

- Strategy must not execute orders.
- Strategy must not call Broker API.
- Strategy must not persist data directly.
- Strategy must not bypass the Risk Engine.

---

## 8. Agentic-AI Decision Workflow

Goal:

Use an LLM-powered agent or pipeline to produce a validated `TradingDecision`.

Flow:

1. Execution Module identifies strategy type `AGENTIC_AI`.
2. Agentic AI strategy delegates to Agent Module.
3. Agent Module builds agent input.
4. Agent Module builds prompt.
5. Agent Module calls LLM Provider.
6. Agent Module stores raw LLM output.
7. Agent Module parses output.
8. If output is invalid, Agent Module attempts repair.
9. If repair succeeds, parsed output is used.
10. If repair fails, fallback decision is `HOLD`.
11. Agent Module creates one or more `AgentDecisionLog` records.
12. Agent Module returns standardized `TradingDecision`.
13. Backend stores `TradingDecision`.
14. Backend passes decision to Risk Engine.

Pipeline mode:

1. Market Analyst Agent creates market analysis.
2. Trading Decision Agent creates proposed action.
3. Agent Risk Manager may critique or adjust the proposal.
4. Final agent output becomes a `TradingDecision`.
5. System Risk Engine still validates the decision.

Important rules:

- LLM output must never be executed directly.
- Agent Risk Manager is not a replacement for the system Risk Engine.
- Agent logs must preserve inputs, prompts, raw outputs, parsed outputs, and repair attempts.

---

## 9. Risk Check Workflow

Goal:

Validate a `TradingDecision` before execution.

Flow:

1. Risk Engine receives `TradingDecision`.
2. Risk Engine loads current portfolio state and relevant experiment config.
3. Risk Engine evaluates risk rules.
4. Risk Engine determines final action.
5. Risk Engine determines final quantity or notional if applicable.
6. Risk Engine creates `RiskCheck`.
7. Backend stores `RiskCheck`.
8. Execution Module uses only the risk-checked result.

Possible outputs:

- approved `BUY`
- approved `SELL`
- approved or forced `HOLD`
- rejected decision converted to `HOLD`

Important rules:

- No order may be created without a `RiskCheck`.
- Risk Engine is authoritative.
- Invalid decisions must not be executed.

---

## 10. Order and Trade Workflow

Goal:

Execute approved actions and store execution results.

Flow:

1. Execution Module receives `RiskCheck`.
2. If `final_action = HOLD`, no order is created.
3. If `final_action = BUY` or `SELL`, Execution Module creates an `Order`.
4. In simulation mode, the order is filled according to simulation rules.
5. In paper-trading mode, order is submitted through Broker Module.
6. If an order receives fills, backend creates one `Trade` per fill. One order may therefore create zero, one, or many trades.
7. Backend updates portfolio state.
8. Backend records portfolio and metric snapshots.

Important distinctions:

- Order means requested execution.
- Trade means actual execution.
- Failed or rejected orders may not create trades.

---

## 11. Metrics Workflow

Goal:

Calculate performance after every execution step.

Flow:

1. Execution step finishes decision and execution phase.
2. Backend updates portfolio state.
3. Backend stores `PortfolioSnapshot`.
4. Metrics Module reads portfolio snapshots and trades.
5. Metrics Module calculates:
   - total return
   - profit/loss
   - number of trades
   - max drawdown
   - buy-and-hold return
   - difference to buy and hold
6. Backend stores `MetricSnapshot`.

Important rules:

- Metrics must be updated after every execution step.
- Metrics must be reproducible from stored snapshots and trades.
- Buy and Hold should be represented as its own experiment.

---

## 12. Broker Synchronization Workflow

Goal:

Keep local paper-trading state aligned with broker state.

Status:

This workflow is deferred. The M9 paper-trading path does not implement broker
account/position reconciliation, outbox processing, scheduled broker sync, or
broker-state mismatch pause policy.

Flow:

1. Backend submits or observes paper order.
2. Broker Module retrieves account cash, positions, and order status.
3. Broker Module compares broker state with local state.
4. Backend stores `BrokerSyncLog`.
5. If states match, local state is updated from broker data.
6. If states mismatch, backend stores `BROKER_STATE_MISMATCH` event.
7. Backend pauses the experiment.

Important rules:

- Broker state is source of truth in paper-trading mode.
- State mismatch must not be ignored.
- Experiment must be paused on mismatch.

---

## 13. Error Handling Workflow

Goal:

Handle failures safely and audibly.

Common error cases:

- market data missing
- strategy error
- invalid LLM output
- repair prompt failed
- risk limit triggered
- order failed
- broker sync failed
- broker state mismatch

General flow:

1. Error occurs during execution.
2. Backend classifies the error.
3. Backend stores a `SystemEventLog`.
4. Backend applies the safe fallback behavior.
5. Backend marks the execution step as `SKIPPED` or `FAILED` if needed.
6. Backend updates experiment status if needed.

Fallback examples:

- missing market data → skip step
- invalid LLM output after repair → HOLD
- risk limit violation → HOLD or stop/pause depending on config
- broker state mismatch → PAUSED

Important rule:

The system must prefer not trading over executing uncertain or unsafe decisions.

---

## 14. Related Documents

- `./entities.md`
- `./business-rules.md`
- `../01_architecture/01_c4-model/c4-component.md`
- `../01_architecture/decisions.md`
- `../03_database/schema.dbml`
- `../05_backend/service-contracts.md`
