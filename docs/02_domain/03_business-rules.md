# Business Rules

## 1. Purpose

This document defines the core business rules for Trading Lab.

These rules constrain how experiments, strategies, agents, risk checks, orders, trades, broker integration, metrics, and logs must behave.

Business rules in this document are binding for implementation. Developers and AI coding agents must not bypass them without an explicit architecture or domain decision update.

---

## 2. Version 1 Scope Rules

### BR-001: SPY is the only tradable asset in V1

Version 1 supports only `SPY` as `asset_symbol`.

Any attempt to configure another asset must be rejected or explicitly treated as unsupported.

---

### BR-002: Real-money trading is out of scope

Version 1 must not support real-money trading.

The system must not use live-trading broker endpoints.

Only internal simulation and paper trading are allowed.

---

### BR-003: Paper trading must use paper endpoints only

Paper-trading experiments must use broker paper-trading endpoints.

If a live broker endpoint is detected, the system must reject the configuration or fail safely.

---

### BR-004: One experiment uses one strategy type

An experiment must have exactly one configured strategy type:

- `BUY_AND_HOLD`
- `MOVING_AVERAGE`
- `AGENTIC_AI`
- `OPENING_RANGE_BREAKOUT`

Strategy comparisons must be represented as multiple experiments, not as multiple strategy types inside one experiment.

---

### BR-005: One experiment has one current portfolio

An experiment must have exactly one current `Portfolio`.

In V1, the portfolio may hold at most one position, expected to be SPY.

---

## 3. Experiment Lifecycle Rules

### BR-006: Experiments must start in CREATED status

A newly created experiment must have status `CREATED`.

It must not start automatically after creation.

---

### BR-007: Only valid status transitions are allowed

Allowed transitions:

```text
CREATED → RUNNING
RUNNING → PAUSED
PAUSED → RUNNING
RUNNING → STOPPED
PAUSED → STOPPED
RUNNING → COMPLETED
RUNNING → FAILED
```

Invalid transitions must be rejected.

`start` is valid only for `CREATED` experiments. `resume` is valid only for `PAUSED` experiments.

---

### BR-008: Completed and stopped experiments must not resume in V1

Experiments with status `COMPLETED` or `STOPPED` must not be resumed in Version 1.

A new experiment should be created instead.

---

### BR-009: Failed experiments require explicit inspection

If an experiment reaches `FAILED`, it should not continue automatically.

The error must be visible through `SystemEventLog` records.

---

## 4. Execution Step Rules

### BR-010: Every strategy execution must create an ExecutionStep

Every historical, scheduled, or manual strategy execution must be represented by an `ExecutionStep`.

---

### BR-011: ExecutionStep sequence numbers must be unique per experiment

Each `ExecutionStep` must have a `sequence_number` unique within its experiment.

---

### BR-012: ExecutionStep trigger type must reflect how it was started

Valid trigger types:

- `HISTORICAL`
- `SCHEDULED`
- `MANUAL`

Manual and scheduled execution must use the same business pipeline.

`DAILY` frequency means daily bar evaluation cadence. It does not guarantee one
trade per day; strategies may produce `HOLD`, risk may convert executable
actions to `HOLD`, and missing market data may fail safely.

`INTRADAY_5_MIN` frequency means five-minute bar evaluation cadence. In the
current implementation it is supported only by Opening Range Breakout historical
simulation using deterministic local SPY fixture data by default or Alpaca
historical 5-minute bars when configured.

---

### BR-013: Concurrent execution for the same experiment is not allowed

The system must not run two execution steps for the same experiment at the same time.

---

### BR-014: Every completed execution step must be auditable

A completed execution step should have the relevant artifacts:

- market data snapshot
- trading decision
- risk check
- portfolio snapshot
- metric snapshot

If an order or trade occurred, those must also be linked.

---

## 5. Market Data Rules

### BR-015: Market data must be accessed through the Market Data Module

Strategies, agents, and frontend code must not call external market data providers directly.

---

### BR-016: Market data used for a decision must be snapshotted

Every decision must be linked to the `MarketDataSnapshot` used to produce it.

---

### BR-017: Missing market data must not produce a trade

If required market data is missing, the execution step must be skipped or failed safely.

The system must store an auditable failure. The current implementation records
`EXPERIMENT_FAILED` with diagnostic details such as
`details_json.errorCode = MARKET_DATA_MISSING`; it does not require a dedicated
new event type for every failure category.

---

## 6. Strategy Rules

### BR-018: Strategies only produce TradingDecisions

Strategies must not create orders, trades, or broker calls.

They only produce standardized `TradingDecision` objects.

---

### BR-019: Strategy output must use supported actions

A strategy decision must use one of:

- `BUY`
- `SELL`
- `HOLD`

Unsupported actions must be rejected or converted to safe fallback behavior.

---

### BR-020: Buy and Hold buys once, then holds

The Buy-and-Hold strategy should buy SPY at the start of the experiment if no position exists.

After entering the position, it should hold.

---

### BR-021: Moving Average strategy follows configured window

The Moving Average strategy must use the configured moving average window.

Default expected V1 value:

```text
200 trading days
```

---

### BR-022: Moving Average strategy can buy, sell, or hold

Expected V1 behavior:

- price above moving average and no position → `BUY`
- price above moving average and already positioned → `HOLD`
- price below moving average and positioned → `SELL`
- price below moving average and no position → `HOLD`

---

### BR-022A: Opening Range Breakout uses the regular-session opening range

Opening Range Breakout is supported for `OPENING_RANGE_BREAKOUT` +
`HISTORICAL_SIMULATION` + `INTRADAY_5_MIN` + `SPY`.

It uses US equities regular sessions, interpreted in America/New_York local
time, with timestamps representing 5-minute bar starts. Full sessions usually
run 09:30-16:00. Early-close sessions may close earlier, for example 13:00.

The opening range is the first 30 minutes:

- 09:30
- 09:35
- 09:40
- 09:45
- 09:50
- 09:55

`openingRangeHigh` is the maximum high across those bars. `openingRangeLow` is
the minimum low across those bars.

Before the opening range is complete, the strategy returns `HOLD`. After the
opening range is complete:

- close above opening range high and no position → `BUY`
- close below opening range low and holding SPY → `SELL`
- final regular-session bar and holding SPY → `SELL`
- otherwise → `HOLD`

M16 allows at most one completed round trip per session. `SELL` only closes an
existing long SPY position and must never open a short position.

Opening Range Breakout uses local deterministic intraday CSV fixture data by
default. When `MARKET_DATA_PROVIDER=alpaca`, it uses Alpaca historical
five-minute SPY bars through the Market Data Module. Bars are validated against
the US equities trading calendar. Full sessions require 09:30 through 15:55 bar
starts. A 13:00 early-close session requires 09:30 through 12:55 bar starts.
Weekends and full market holidays require no bars. Missing expected session bars
are fatal; there is no forward-fill or interpolation.

For paper trading, Opening Range Breakout is scheduled-only. It evaluates only
completed regular-session 5-minute bars, skips before step creation when the
expected completed bar is unavailable, and does not backfill missed slots.

---

## 7. Agentic-AI Rules

### BR-023: Agentic AI is a strategy type

Agentic AI must be integrated as `strategy_type = AGENTIC_AI`.

It must follow the same execution pipeline as rule-based strategies.

---

### BR-024: LLM output must never execute directly

LLM output must not create orders or trades directly.

It must first be converted into a standardized `TradingDecision`.

---

### BR-025: Agent decisions must be logged

Agentic-AI experiments must store relevant `AgentDecisionLog` records.

Logs should include:

- input JSON
- prompt text
- raw output text
- parsed output JSON
- parsing status
- repair prompt if used
- repair output if used

---

### BR-026: Invalid LLM output must trigger repair

If LLM output is invalid, the Agent Module must attempt a repair prompt.

---

### BR-027: Failed repair falls back to HOLD

If repair fails, the system must use `HOLD` as fallback.

Fallback details must be auditable in `AgentDecisionLog`. A dedicated
`FALLBACK_HOLD_USED` system event is not required by the current implementation.

---

### BR-027A: ScaDS.AI paper agent scope

ScaDS.AI may be used only for `PAPER_TRADING` + `AGENTIC_AI` +
`SINGLE_AGENT` + `DAILY` + `SPY` when `SCADSAI_LLM_ENABLED=true`, an API key is
configured, and the selected model is in `SCADSAI_ALLOWED_MODELS`.

Historical Agentic-AI execution remains deterministic and uses fake providers.
Pipeline-agent paper trading, ORB/intraday agent trading, prompt editing, tool
calling, and direct agent access to broker, Alpaca, scheduler, persistence,
environment, or secret APIs are out of scope.

---

### BR-028: Agent Risk Manager is not the system Risk Engine

A pipeline agent may include an agent step named `RISK_MANAGER`.

This does not replace the system Risk Engine.

Every final agent decision must still pass through the system Risk Engine.

---

## 8. Risk Rules

### BR-029: Every TradingDecision must pass through RiskCheck

No `TradingDecision` may be executed without a corresponding `RiskCheck`.

---

### BR-030: Risk Engine is authoritative

Strategies and agents may suggest actions and sizes.

The Risk Engine decides the final executable action and size.

---

### BR-031: SELL without position is forbidden

The system must not execute a `SELL` if the portfolio does not have sufficient position quantity.

---

### BR-032: BUY without sufficient cash is forbidden

The system must not execute a `BUY` that would make cash negative.

---

### BR-033: Short selling is forbidden in V1

The system must not allow positions to become negative.

---

### BR-034: Margin trading is forbidden in V1

The system must not allow purchases beyond available cash and configured limits.

---

### BR-035: Maximum executable size must be controlled

The current implementation sizes BUY orders from available cash using whole
shares. Broader max-position-percent risk limits are documented for future
expansion.

---

### BR-036: Maximum trade frequency must be enforced

Max trades per day or week are future risk-rule extensions and are not enforced
by the current implementation.

---

### BR-037: Max drawdown limit must be enforced if configured

Max drawdown pause/stop/block policies are future risk-rule extensions and are
not enforced by the current implementation.

---

## 9. Order and Trade Rules

### BR-038: HOLD does not create an Order

A final action of `HOLD` must not create an executable order.

---

### BR-039: Orders are created only after RiskCheck

An order may be created only from an approved or adjusted `RiskCheck`.

---

### BR-040: Trades are created only after execution

A `Trade` must be created only when an order is actually filled in simulation or paper trading.

---

### BR-040A: One order may produce multiple trades

One order may produce multiple trades. Partial fills must be represented as separate `Trade` records linked to the same `Order`.

---

### BR-041: Failed or rejected orders must not create trades

If an order is rejected or failed, no trade should be created.

The failure must be logged.

Transient broker or market-data failures in scheduled paper trading fail the
current `ExecutionStep` but keep the experiment `RUNNING` when no durable broker
side effect is known. Configuration and safety failures remain experiment-fatal.
For ORB paper trading, an unavailable expected completed bar is treated as a
scheduler skip before step creation rather than a failed execution step.

---

### BR-042: Order and Trade must remain distinguishable

The system must not collapse orders and trades into the same domain concept.

---

## 10. Portfolio Rules

### BR-043: Cash must not become negative

Portfolio cash must never become negative through simulation or paper-trading state updates.

---

### BR-044: Position quantity must not become negative

Position quantity must never become negative in V1.

BUY execution uses available cash and whole-share rounding. `SELL` always
liquidates the existing long SPY position and must never open a short position.
If available cash cannot buy one whole share, the final action becomes `HOLD`
with an auditable reason.

---

### BR-045: Portfolio value must be calculated consistently

Portfolio value should be calculated as:

```text
cash + position_quantity * current_price
```

for the V1 single-position model.

---

### BR-046: PortfolioSnapshot must be recorded after execution

After each completed execution step, the system should record a `PortfolioSnapshot`.

---

## 11. Metrics Rules

### BR-047: Metrics must update after each execution step

The system must create or update a `MetricSnapshot` after each execution step.

---

### BR-048: Metrics must be reproducible

Metrics should be reproducible from stored portfolio snapshots and trades.

---

### BR-049: Buy and Hold is a benchmark experiment

Buy and Hold benchmark experiments are normal experiments with `strategy_type = BUY_AND_HOLD`. Metric snapshots may store denormalized fields such as `buy_and_hold_return` and `difference_to_buy_and_hold`.

---

### BR-050: Max drawdown must use portfolio value history

Max drawdown must be calculated from historical portfolio values, not from isolated trades.

---

## 12. Broker Rules

### BR-051: Broker access must go through Broker Module

Strategies, agents, API routes, and frontend code must not call Broker API directly.

---

### BR-052: Broker is source of truth in paper-trading mode

For fully reconciled paper-trading workflows, broker cash, positions, and order
state should be authoritative. The current M9 implementation does not perform
broker account/position reconciliation; it updates local state from immediate
paper order responses only.

---

### BR-053: Broker state mismatch pauses experiment

Deferred.

If local state and broker state diverge, the system must:

1. record a `BrokerSyncLog`
2. record a `BROKER_STATE_MISMATCH` event
3. pause the affected experiment

The mismatch pause workflow is not implemented in the current M9 path.

---

### BR-054: Broker failures must be logged

Broker API failures must be recorded as system events.

---

## 13. Event and Logging Rules

### BR-055: Important lifecycle events must be logged

The system should log important lifecycle events such as:

- experiment created
- experiment started
- experiment paused
- experiment stopped
- experiment completed

---

### BR-056: Errors must be logged as SystemEventLog

Errors must be stored as `SystemEventLog` records with an appropriate level and event type.

---

### BR-057: Risk limit triggers must be logged

When a risk rule blocks or modifies a decision, the result must be auditable in
`RiskCheck`. Dedicated `RISK_LIMIT_TRIGGERED` system events are a future
extension unless explicitly emitted by an implemented path.

---

### BR-058: Agent parsing failures must be logged

Invalid deterministic agent outputs and repair attempts must be logged in
`AgentDecisionLog`. Real LLM providers are not implemented.

---

### BR-059: Every executed trade must be auditable

Every trade must be traceable to:

- experiment
- execution step
- market data snapshot
- trading decision
- risk check
- order
- trade
- portfolio snapshot
- metric snapshot

---

### BR-059A: Paper smoke-test strategy is diagnostics-only

`PAPER_TRADING_SMOKE_TEST` is disabled by default and may run only when
`PAPER_TRADING_TEST_MODE_ENABLED=true`.

It supports only:

- `PAPER_TRADING`
- `TEST_1_MIN`
- `SPY`
- scheduled execution during US regular market hours
- fixed 1-share BUY when no local SPY position exists
- SELL only to close the existing local SPY position

It is not an investment strategy, must never short, and must still pass through
TradingDecision -> RiskCheck -> Order/Trade.

---

## 14. Out-of-Scope Rules

### BR-060: No User entity in V1

Version 1 is designed for a single user and does not include user registration or multi-user ownership.

---

### BR-061: No separate Position entity in V1

Version 1 stores the single SPY position directly in `Portfolio` and `PortfolioSnapshot`.

A separate `Position` entity is a future extension.

---

### BR-062: No options, margin, or short selling in V1

These trading modes are explicitly out of scope.

---

### BR-063: No public financial advice

The system is a research and experimentation platform.

It must not present itself as financial advice.

---

## 15. Related Documents

- `./entities.md`
- `./workflows.md`
- `../01_architecture/decisions.md`
- `../01_architecture/02_adr/ADR-005-risk-engine-before-execution.md`
- `../01_architecture/02_adr/ADR-009-paper-trading-only.md`
- `../03_database/schema.dbml`
- `../05_backend/service-contracts.md`
