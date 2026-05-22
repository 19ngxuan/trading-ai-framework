# Domain Entities

## 1. Purpose

This document describes the core domain entities of Trading Lab.

It defines the business meaning of each entity, its main responsibility, and its relationship to other entities. It is intended for developers and AI coding agents working on the system.

This document is not the final database schema. The technical schema is documented separately in `../04_database/schema.dbml`.

---

## 2. Domain Model Overview

Trading Lab is centered around experiments.

An `Experiment` represents one strategy or agentic-AI trading run. Each experiment owns its configuration, portfolio state, execution steps, decisions, orders, trades, snapshots, metrics, and logs.

The core audit chain is:

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
```

For agentic-AI experiments, the chain additionally includes:

```text
ExecutionStep
→ AgentDecisionLog[]
→ TradingDecision
```

The central design principle is that every executed trade must be traceable back to the market data, decision, risk validation, and execution result that caused it.

---

## 3. Entity Relationship Summary

High-level relationships:

```text
Experiment 1 ── 1 StrategyConfig
Experiment 1 ── 1 Portfolio
Experiment 1 ── n ExecutionStep

ExecutionStep 1 ── 1 MarketDataSnapshot
ExecutionStep 1 ── 1 TradingDecision
ExecutionStep 1 ── 1 RiskCheck
ExecutionStep 1 ── 0..1 Order
ExecutionStep 1 ── 0..1 Trade
ExecutionStep 1 ── 1 PortfolioSnapshot
ExecutionStep 1 ── 1 MetricSnapshot
ExecutionStep 1 ── 0..n AgentDecisionLog
ExecutionStep 1 ── 0..n BrokerSyncLog
ExecutionStep 1 ── 0..n SystemEventLog

TradingDecision 1 ── 1 RiskCheck
RiskCheck 1 ── 0..1 Order
Order 1 ── 0..1 Trade
```

Notes:

- A `HOLD` decision usually does not create an `Order`.
- A blocked decision does not create an `Order`.
- A failed order may exist without a `Trade`.
- Rule-based strategies usually do not create `AgentDecisionLog` records.
- Agentic-AI strategies may create one or multiple `AgentDecisionLog` records per execution step.

---

## 4. Core Entities

## 4.1 Experiment

An `Experiment` is the root aggregate of the domain model.

It represents one configured trading run.

Examples:

- Buy-and-Hold historical simulation for SPY
- 200-day Moving Average historical simulation for SPY
- Agentic-AI paper-trading experiment for SPY

Main fields:

- `id`
- `name`
- `mode`
- `strategy_type`
- `asset_symbol`
- `status`
- `initial_capital`
- `start_date`
- `end_date`
- `trading_frequency`
- `fee_model_type`
- `fee_value`
- `created_at`
- `updated_at`

Main responsibilities:

- define what is being tested
- define the experiment mode
- define the selected strategy type
- define the traded asset
- define the capital, time range, frequency, and fee model
- own all execution steps and results

Version 1 constraints:

- `asset_symbol` is limited to `SPY`
- one experiment uses one strategy type
- one experiment has one portfolio
- one experiment has one strategy configuration

---

## 4.2 StrategyConfig

A `StrategyConfig` stores the configuration for the strategy used by an experiment.

It is separated from `Experiment` because different strategy types require different parameters.

Main fields:

- `id`
- `experiment_id`
- `strategy_type`
- `strategy_version`
- `moving_average_window`
- `position_sizing_type`
- `agent_mode`
- `model_name`
- `confidence_threshold`
- `parameters_json`
- `created_at`
- `updated_at`

Responsibilities:

- store strategy-specific configuration
- store the strategy version used by an experiment
- support flexible strategy parameters through `parameters_json`

Examples:

Moving Average strategy:

```json
{
  "movingAverageWindow": 200,
  "positionSizingType": "ALL_IN",
  "tradeOnCrossOnly": false
}
```

Agentic-AI strategy:

```json
{
  "agentMode": "SINGLE_AGENT",
  "modelName": "gpt-4.1",
  "confidenceThreshold": 0.65,
  "useRsi": true,
  "useNewsSentiment": false
}
```

---

## 4.3 Portfolio

A `Portfolio` represents the current portfolio state of an experiment.

In Version 1, the portfolio model is intentionally simple because only SPY is supported.

Main fields:

- `id`
- `experiment_id`
- `cash`
- `position_symbol`
- `position_quantity`
- `current_price`
- `current_position_value`
- `current_portfolio_value`
- `updated_at`

Responsibilities:

- hold current cash
- hold current SPY position
- hold current portfolio valuation
- represent the latest known state of an experiment

Version 1 simplification:

- one portfolio may hold at most one position
- the position is expected to be SPY

Future extension:

- a separate `Position` entity may be added for multi-asset portfolios

---

## 4.4 ExecutionStep

An `ExecutionStep` represents one strategy or agent execution event.

It is the central audit unit of the system.

Examples:

- one historical simulation step
- one scheduled paper-trading step
- one manually triggered debug step

Main fields:

- `id`
- `experiment_id`
- `scheduled_for`
- `started_at`
- `completed_at`
- `status`
- `trigger_type`
- `sequence_number`
- `error_message`
- `created_at`

Responsibilities:

- represent one execution cycle
- connect market data, decision, risk check, order, trade, snapshots, metrics, and logs
- make each system action auditable

Important rule:

Every strategy or agent execution must create an `ExecutionStep`.

---

## 4.5 MarketDataSnapshot

A `MarketDataSnapshot` stores the market data used during one execution step.

Main fields:

- `id`
- `execution_step_id`
- `experiment_id`
- `timestamp`
- `symbol`
- `price`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `moving_average`
- `rsi`
- `raw_data_json`
- `created_at`

Responsibilities:

- capture the exact market data visible to a strategy or agent
- support reproducibility and auditing
- provide inputs for technical strategies and agentic-AI decisions

Important rule:

A decision must reference the market data snapshot that was used to produce it.

---

## 4.6 TradingDecision

A `TradingDecision` is the standardized output of a rule-based strategy or agentic-AI strategy.

It represents what the strategy or agent wants to do before system risk validation.

Main fields:

- `id`
- `execution_step_id`
- `experiment_id`
- `market_data_snapshot_id`
- `source_type`
- `source_name`
- `action`
- `symbol`
- `suggested_quantity`
- `suggested_notional`
- `confidence`
- `reason`
- `raw_decision_json`
- `created_at`

Possible actions:

- `BUY`
- `SELL`
- `HOLD`

Responsibilities:

- normalize outputs from different strategies and agents
- store intended action before risk validation
- preserve explanation and confidence when available

Important rules:

- strategies and agents only produce `TradingDecision`
- a `TradingDecision` must not be executed directly
- every `TradingDecision` must pass through a `RiskCheck`

---

## 4.7 RiskCheck

A `RiskCheck` represents the system-level validation of a `TradingDecision`.

It determines whether a decision may be executed and what the final executable action is.

Main fields:

- `id`
- `execution_step_id`
- `experiment_id`
- `trading_decision_id`
- `approved`
- `final_action`
- `final_quantity`
- `final_notional`
- `rejection_reason`
- `rules_triggered_json`
- `created_at`

Responsibilities:

- enforce system risk rules
- block invalid or unsafe decisions
- adjust suggested size if necessary
- convert decisions to `HOLD` when required

Important rules:

- no order may be created without a `RiskCheck`
- the Risk Engine is authoritative over strategy and agent suggestions
- agent-suggested position sizes may be reduced or rejected

---

## 4.8 Order

An `Order` represents an intended execution after risk validation.

It may be simulated internally or submitted to a paper broker.

Main fields:

- `id`
- `execution_step_id`
- `experiment_id`
- `risk_check_id`
- `mode`
- `broker_name`
- `broker_order_id`
- `symbol`
- `side`
- `quantity`
- `order_type`
- `status`
- `submitted_at`
- `filled_at`
- `average_fill_price`
- `error_message`
- `created_at`

Responsibilities:

- represent the order created from an approved risk check
- track order status
- support both simulated and paper broker execution

Important distinctions:

- an order is not the same as a trade
- an order may be rejected or fail
- a `HOLD` decision does not create an order

---

## 4.9 Trade

A `Trade` represents an actually executed transaction.

Main fields:

- `id`
- `execution_step_id`
- `experiment_id`
- `order_id`
- `timestamp`
- `symbol`
- `side`
- `quantity`
- `price`
- `order_value`
- `fee`
- `portfolio_value_after_trade`
- `created_at`

Responsibilities:

- record actual executed buys and sells
- support portfolio updates
- support metric calculations
- provide an audit trail for executed orders

Important distinction:

```text
Order = request to execute
Trade = actual execution result
```

---

## 4.10 PortfolioSnapshot

A `PortfolioSnapshot` stores the portfolio state after an execution step.

Main fields:

- `id`
- `execution_step_id`
- `experiment_id`
- `timestamp`
- `cash`
- `position_symbol`
- `position_quantity`
- `position_market_value`
- `total_portfolio_value`
- `current_price`
- `created_at`

Responsibilities:

- support performance charts
- support max drawdown calculation
- support historical reconstruction of portfolio value
- support experiment comparison

Important rule:

A portfolio snapshot should be stored after every execution step.

---

## 4.11 MetricSnapshot

A `MetricSnapshot` stores calculated performance metrics after an execution step.

Main fields:

- `id`
- `execution_step_id`
- `experiment_id`
- `timestamp`
- `total_return`
- `profit_loss`
- `number_of_trades`
- `max_drawdown`
- `buy_and_hold_return`
- `difference_to_buy_and_hold`
- `created_at`

Responsibilities:

- track experiment performance over time
- support dashboard metrics
- support comparison views
- support benchmark comparison

Important rule:

Metrics must be reproducible from stored trades and portfolio snapshots.

---

## 4.12 AgentDecisionLog

An `AgentDecisionLog` stores the details of an agentic-AI step.

It exists only for agentic-AI experiments.

Main fields:

- `id`
- `execution_step_id`
- `experiment_id`
- `trading_decision_id`
- `agent_mode`
- `agent_step_name`
- `agent_name`
- `prompt_version`
- `model_name`
- `model_version`
- `input_json`
- `prompt_text`
- `raw_output_text`
- `parsed_output_json`
- `parsing_status`
- `repair_prompt_text`
- `repair_raw_output_text`
- `created_at`

Responsibilities:

- store agent inputs
- store prompts
- store raw LLM outputs
- store parsed outputs
- store repair attempts
- support debugging and auditing of agent decisions

Pipeline mode:

A pipeline-agent execution may create multiple `AgentDecisionLog` records for one `ExecutionStep`.

Examples:

- `MARKET_ANALYST`
- `TRADING_DECISION`
- `RISK_MANAGER`

Important rule:

LLM output must never be executed directly. It must first become a validated `TradingDecision` and then pass through the system `RiskCheck`.

---

## 4.13 BrokerSyncLog

A `BrokerSyncLog` stores synchronization results between local state and broker state.

Main fields:

- `id`
- `execution_step_id`
- `experiment_id`
- `timestamp`
- `broker_name`
- `sync_status`
- `broker_cash`
- `local_cash`
- `broker_positions_json`
- `local_positions_json`
- `mismatch_details_json`
- `error_message`
- `created_at`

Responsibilities:

- record broker synchronization attempts
- detect local/broker mismatches
- support debugging paper-trading behavior

Important rule:

In paper-trading mode, the broker is the source of truth. If local state and broker state diverge, the experiment must be paused and a mismatch event must be recorded.

---

## 4.14 SystemEventLog

A `SystemEventLog` stores important system events, warnings, and errors.

Main fields:

- `id`
- `execution_step_id`
- `experiment_id`
- `timestamp`
- `level`
- `event_type`
- `message`
- `details_json`
- `created_at`

Responsibilities:

- record important lifecycle events
- record errors
- record risk events
- record broker sync issues
- record LLM parsing and fallback behavior

Examples:

- `EXPERIMENT_STARTED`
- `MARKET_DATA_MISSING`
- `RISK_LIMIT_TRIGGERED`
- `ORDER_FAILED`
- `BROKER_STATE_MISMATCH`
- `LLM_OUTPUT_INVALID`
- `FALLBACK_HOLD_USED`

---

## 5. Domain Enums

The domain uses controlled enum values for core states and categories.

### Experiment

- `experiment_mode`
- `strategy_type`
- `experiment_status`
- `trading_frequency`
- `fee_model_type`

### Execution

- `execution_step_status`
- `trigger_type`
- `trade_action`
- `final_action`

### Decision and Order

- `decision_source_type`
- `order_mode`
- `broker_name`
- `order_side`
- `order_type`
- `order_status`

### Agentic AI

- `agent_mode`
- `agent_step_name`
- `parsing_status`

### Broker Sync and Events

- `broker_sync_status`
- `event_level`
- `system_event_type`

The exact enum values are defined in the database schema and should remain aligned with backend domain enums.

---

## 6. Important Domain Distinctions

## 6.1 Experiment vs ExecutionStep

An `Experiment` is the full configured run.

An `ExecutionStep` is one execution cycle inside that experiment.

---

## 6.2 TradingDecision vs RiskCheck

A `TradingDecision` is what a strategy or agent wants to do.

A `RiskCheck` is what the system allows to happen.

The system must execute only the risk-checked result.

---

## 6.3 Order vs Trade

An `Order` is an execution request.

A `Trade` is an actual executed transaction.

Orders may fail or be rejected. Trades only exist after execution.

---

## 6.4 Portfolio vs PortfolioSnapshot

A `Portfolio` stores the current state.

A `PortfolioSnapshot` stores historical state after an execution step.

---

## 6.5 Agent Risk Manager vs System Risk Engine

A pipeline agent may contain an agent role named `RISK_MANAGER`.

This is not the same as the system Risk Engine.

The system Risk Engine remains mandatory and authoritative.

---

## 7. Version 1 Simplifications

Version 1 intentionally simplifies the domain:

- one user only
- no user entity
- one asset only: SPY
- no multi-asset portfolio
- no separate Position entity
- no real-money trading
- no short selling
- no margin trading
- no options trading
- no authentication module
- no external worker service

These simplifications keep the initial system implementable while preserving extension points for later versions.

---

## 8. Future Extensions

Potential future entities:

- `User`
- `Position`
- `BrokerAccount`
- `PromptVersion`
- `StrategyVersion`
- `ExperimentGroup`
- `BacktestDataset`
- `Watchlist`

These entities must not be introduced in V1 unless the architecture and schema are explicitly updated.

---

## 9. Related Documents

- `../01_architecture/system-overview.md`
- `../01_architecture/c4-component.md`
- `../01_architecture/decisions.md`
- `./workflows.md`
- `./business-rules.md`
- `../04_database/schema.dbml`
- `../06_backend/service-contracts.md`
