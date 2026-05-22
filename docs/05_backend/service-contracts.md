# Backend Service Contracts

## 1. Purpose

This document defines the internal service contracts between backend modules in Trading Lab.

The goal is to keep module boundaries explicit and prevent architecture drift during implementation.

The most important architectural rule is:

```text
Strategy / Agent
→ TradingDecision
→ RiskEngine
→ ExecutionEngine
→ Order / Trade
```

Strategies and agents decide. They do not execute.

---

## 2. Contract Principles

All backend contracts follow these principles:

1. Services communicate through explicit inputs and outputs.
2. Strategies and agents return standardized trading decisions.
3. Every decision must be validated by the Risk Engine.
4. The Execution Engine executes only approved or adjusted decisions.
5. External systems are accessed only through adapters.
6. Persistence should go through repositories.
7. Every execution step must be auditable.

---

## 3. Core Domain Types

The exact implementation may use Pydantic models, dataclasses, or domain value objects. The following conceptual types must exist.

## 3.1 StrategyContext

Represents all information required by a strategy to produce a decision.

Conceptual fields:

```text
experiment
strategy_config
market_data_snapshot
portfolio_state
previous_trades
current_metrics
execution_timestamp
```

Rules:

- The context is read-only from the strategy perspective.
- Strategies must not load additional data directly from repositories or external providers.
- Strategies must not mutate portfolio state.

---

## 3.2 TradingDecision

Standardized output produced by a strategy or agent.

Conceptual fields:

```text
action: BUY | SELL | HOLD
symbol: string
suggested_quantity: decimal | null
suggested_notional: decimal | null
confidence: decimal | null
reason: string | null
source_type: STRATEGY | AGENT
source_name: string | null
raw_decision_json: object | null
```

Rules:

- Every strategy and agent must return a `TradingDecision`.
- `TradingDecision` is not executable by itself.
- `TradingDecision` must always go through the Risk Engine.

---

## 3.3 RiskCheck

Output produced by the Risk Engine.

Conceptual fields:

```text
approved: boolean
final_action: BUY | SELL | HOLD
final_quantity: decimal | null
final_notional: decimal | null
rejection_reason: string | null
rules_triggered_json: object | null
```

Rules:

- No order may be created without a `RiskCheck`.
- The Risk Engine is authoritative.
- Agent-proposed sizing may be reduced, rejected, or converted to HOLD.

---

## 3.4 ExecutionResult

Output produced by the Execution Engine.

Conceptual fields:

```text
order: Order | null
trade: Trade | null
portfolio_state: PortfolioState
status: COMPLETED | SKIPPED | FAILED
error_message: string | null
```

Rules:

- HOLD decisions normally create no order.
- Failed execution must produce a system event.
- Portfolio updates must remain consistent.

---

## 3.5 PortfolioState

Represents current portfolio state for one experiment.

Conceptual fields:

```text
cash
position_symbol
position_quantity
current_price
current_position_value
current_portfolio_value
```

Version 1 rule:

- A portfolio has at most one position: SPY.

Future extension:

- Multi-asset support may introduce a separate Position entity.

---

## 4. Experiment Service Contract

## 4.1 create_experiment

Conceptual signature:

```text
create_experiment(request) -> ExperimentWithPortfolio
```

Responsibility:

- validate experiment configuration
- create experiment
- create strategy configuration
- create initial portfolio
- return created experiment and portfolio

Must enforce:

- asset is SPY in V1
- mode is valid
- strategy type is valid
- start and end dates are valid
- initial capital is positive
- status starts as CREATED

Must not:

- start execution automatically
- call broker APIs
- call LLM provider

---

## 4.2 start_experiment

Conceptual signature:

```text
start_experiment(experiment_id) -> ExperimentStatus
```

Responsibility:

- validate status transition
- set experiment to RUNNING
- schedule or trigger execution depending on mode

Allowed starting statuses:

- CREATED
- PAUSED, only for resume semantics if routed through resume

Must reject:

- RUNNING
- STOPPED
- COMPLETED
- FAILED

---

## 4.3 pause_experiment

Conceptual signature:

```text
pause_experiment(experiment_id) -> ExperimentStatus
```

Responsibility:

- pause a running experiment
- prevent further scheduled execution

Allowed source status:

- RUNNING

---

## 4.4 resume_experiment

Conceptual signature:

```text
resume_experiment(experiment_id) -> ExperimentStatus
```

Responsibility:

- resume a paused experiment
- re-enable scheduled execution

Allowed source status:

- PAUSED

---

## 4.5 stop_experiment

Conceptual signature:

```text
stop_experiment(experiment_id) -> ExperimentStatus
```

Responsibility:

- stop a running or paused experiment permanently

Allowed source statuses:

- RUNNING
- PAUSED

---

## 5. Scheduler Contract

## 5.1 trigger_due_experiments

Conceptual signature:

```text
trigger_due_experiments(now) -> list[ExecutionStepResult]
```

Responsibility:

- find running experiments due for execution
- trigger one execution step per due experiment
- avoid duplicate concurrent execution

Must not:

- implement trading decisions
- bypass Execution Module

---

## 5.2 run_next_step

Conceptual signature:

```text
run_next_step(experiment_id, trigger_type=MANUAL) -> ExecutionStepResult
```

Responsibility:

- manually trigger exactly one execution step
- use the same pipeline as scheduled execution

Rules:

- Must create an `ExecutionStep`.
- Must not execute if another step for the same experiment is running.

---

## 6. Execution Orchestrator Contract

## 6.1 run_execution_step

Conceptual signature:

```text
run_execution_step(experiment_id, trigger_type, scheduled_for=None) -> ExecutionStepResult
```

Responsibility:

Run one full execution step.

Required sequence:

1. Load experiment.
2. Create `ExecutionStep`.
3. Load market data.
4. Store `MarketDataSnapshot`.
5. Load portfolio state.
6. Build `StrategyContext`.
7. Run strategy or agent.
8. Store `TradingDecision`.
9. Run Risk Engine.
10. Store `RiskCheck`.
11. Execute final action if not HOLD.
12. Store Order and Trade if applicable.
13. Update portfolio.
14. Store `PortfolioSnapshot`.
15. Calculate metrics.
16. Store `MetricSnapshot`.
17. Store `SystemEventLog` records.
18. Mark step as completed, skipped, or failed.

Must enforce:

- every step is persisted
- every decision has a risk check
- failed steps are logged
- missing market data leads to SKIPPED or FAILED according to policy

---

## 7. Strategy Contract

## 7.1 Strategy.decide

Conceptual signature:

```text
decide(context: StrategyContext) -> TradingDecision
```

Responsibilities:

- inspect context
- produce BUY, SELL, or HOLD decision
- provide reason
- optionally provide confidence
- optionally suggest quantity or notional

Rules:

- Must not execute orders.
- Must not update portfolio.
- Must not write to database directly.
- Must not call broker APIs.
- Must not call market data provider directly.
- Must not bypass Risk Engine.

---

## 7.2 BuyAndHoldStrategy

Expected behavior:

- BUY at the first eligible execution step if no position exists.
- HOLD after position exists.
- Use available capital according to configured sizing rules.

---

## 7.3 MovingAverageStrategy

Expected behavior:

- BUY when price is above moving average and no position exists.
- HOLD when price is above moving average and position already exists.
- SELL when price is below moving average and position exists.
- HOLD when price is below moving average and no position exists.
- HOLD or skip safely when moving average is unavailable.

---

## 7.4 AgenticAIStrategy

Expected behavior:

- Delegate agent reasoning to Agent Module.
- Convert agent output into `TradingDecision`.
- Never call broker directly.
- Never execute orders.

---

## 8. Agent Engine Contract

## 8.1 run_agent

Conceptual signature:

```text
run_agent(context: StrategyContext, agent_config) -> TradingDecision
```

Responsibility:

- build agent input
- build prompt
- call LLM client
- parse output
- validate output
- repair invalid output if possible
- log input, prompt, raw output, parsed output, and repair attempts
- return standardized `TradingDecision`

Rules:

- LLM output must never be executed directly.
- Invalid output must trigger repair.
- Failed repair must result in fallback HOLD.
- Every agent decision must be logged.

---

## 8.2 LLMClient.call

Conceptual signature:

```text
call(prompt, model_name, options) -> LLMResponse
```

Responsibility:

- call configured LLM provider
- return raw model response
- handle provider-level errors

Rules:

- Must not contain trading logic.
- Must not parse trading decisions.
- Must not call broker APIs.

---

## 8.3 OutputParser.parse

Conceptual signature:

```text
parse(raw_output) -> ParsedAgentOutput | ParseError
```

Responsibility:

- extract structured JSON
- validate action
- validate symbol
- validate confidence
- validate optional sizing

Allowed actions:

- BUY
- SELL
- HOLD

---

## 9. Risk Engine Contract

## 9.1 evaluate

Conceptual signature:

```text
evaluate(decision, portfolio_state, experiment_config, risk_config, recent_trades, current_metrics) -> RiskCheck
```

Responsibility:

- validate action
- validate symbol
- validate available cash
- validate available position
- apply max position size
- apply max trades per day/week
- apply max drawdown limit
- produce final executable action and size

Must enforce:

- SPY only in V1
- no short selling
- no margin trading
- no selling without position
- no buying without sufficient cash
- no execution without risk check

Fallback:

- Invalid or unsafe decisions become HOLD.

---

## 10. Execution Engine Contract

## 10.1 execute

Conceptual signature:

```text
execute(risk_check, experiment, portfolio_state, market_data_snapshot) -> ExecutionResult
```

Responsibility:

- execute approved final action
- choose simulation or paper-trading provider based on experiment mode
- create order if needed
- create trade if filled
- update portfolio state

Rules:

- If final action is HOLD, do not create order.
- If mode is HISTORICAL_SIMULATION or LIVE_SIMULATION, use simulation provider.
- If mode is PAPER_TRADING, use paper provider and Broker Module.
- Must not execute rejected decisions.

---

## 10.2 SimulationExecutionProvider.execute

Conceptual signature:

```text
execute_simulated_order(risk_check, portfolio_state, market_data_snapshot) -> ExecutionResult
```

Responsibility:

- simulate market order execution
- update cash and position
- create simulated order and trade

Rules:

- Cash must not become negative.
- Position must not become negative.
- Portfolio value must remain consistent.

---

## 10.3 PaperExecutionProvider.execute

Conceptual signature:

```text
execute_paper_order(risk_check, experiment, portfolio_state) -> ExecutionResult
```

Responsibility:

- place paper order through Broker Module
- retrieve order status
- synchronize broker state
- create order and trade records as applicable

Rules:

- Only paper-trading endpoints may be used.
- Broker state is source of truth.
- Broker mismatch pauses experiment.

---

## 11. Market Data Provider Contract

## 11.1 get_historical_data

Conceptual signature:

```text
get_historical_data(symbol, start_date, end_date, frequency) -> list[MarketDataPoint]
```

Responsibility:

- return historical market data for simulation

Rules:

- V1 supports SPY only.
- Missing market data must be handled explicitly.

---

## 11.2 get_latest_snapshot

Conceptual signature:

```text
get_latest_snapshot(symbol) -> MarketDataSnapshotData
```

Responsibility:

- return latest market data for live-like simulation or paper trading

Rules:

- Must not be called directly by strategies or agents.

---

## 12. Broker Adapter Contract

## 12.1 place_order

Conceptual signature:

```text
place_order(symbol, side, quantity, order_type) -> BrokerOrderResult
```

Responsibility:

- submit paper order
- return broker order id and initial status

Rules:

- Must use paper-trading endpoint only.
- Must not support real-money endpoint in V1.

---

## 12.2 get_account_state

Conceptual signature:

```text
get_account_state() -> BrokerAccountState
```

Responsibility:

- retrieve paper account cash and account status

---

## 12.3 get_positions

Conceptual signature:

```text
get_positions() -> list[BrokerPosition]
```

Responsibility:

- retrieve current paper-trading positions

---

## 12.4 get_order_status

Conceptual signature:

```text
get_order_status(broker_order_id) -> BrokerOrderStatus
```

Responsibility:

- retrieve latest broker order status

---

## 12.5 sync_state

Conceptual signature:

```text
sync_state(experiment_id) -> BrokerSyncResult
```

Responsibility:

- compare broker state with local state
- create broker sync log
- pause experiment on mismatch

---

## 13. Metrics Engine Contract

## 13.1 calculate_after_step

Conceptual signature:

```text
calculate_after_step(experiment_id, execution_step_id) -> MetricSnapshot
```

Responsibility:

- calculate metrics after an execution step
- store or return metric snapshot

Metrics:

- total return
- profit/loss
- number of trades
- max drawdown
- Buy-and-Hold return
- difference to Buy-and-Hold

Rules:

- Metrics must be reproducible from stored trades and portfolio snapshots.
- Metrics must not call broker or LLM APIs.

---

## 14. Event Service Contract

## 14.1 log_event

Conceptual signature:

```text
log_event(experiment_id, execution_step_id, level, event_type, message, details_json=None) -> SystemEventLog
```

Responsibility:

- create standardized system events

Rules:

- Important execution events must be logged.
- Errors must be visible through the Events API.
- Event details may use JSON for provider-specific or diagnostic metadata.

---

## 15. Repository Contracts

Repositories encapsulate database access.

Examples:

```text
ExperimentRepository
ExecutionStepRepository
TradingDecisionRepository
RiskCheckRepository
OrderRepository
TradeRepository
MetricRepository
AgentLogRepository
EventRepository
```

Repository rules:

- Repositories should not contain business decisions.
- Repositories should not call external APIs.
- Repositories should not perform strategy, risk, or metric calculations.
- Repositories should expose clear read/write operations for services.

---

## 16. Contract-Level Anti-Patterns

The following patterns are forbidden:

```text
Agent → BrokerAdapter
Strategy → BrokerAdapter
Strategy → Database
Agent → ExecutionEngine
API Route → Broker API
API Route → LLM Provider
Frontend → Alpaca
Frontend → Database
RiskEngine skipped
Order created without RiskCheck
Trade created without Order
Execution without ExecutionStep
```

---

## 17. Related Documents

- `../01_architecture/c4-component.md`
- `../01_architecture/decisions.md`
- `../02_domain/entities.md`
- `../02_domain/workflows.md`
- `../02_domain/business-rules.md`
- `../03_api/api-spec.md`
- `../04_database/schema.dbml`
- `./module-structure.md`
