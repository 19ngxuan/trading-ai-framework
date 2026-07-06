# M23 Rule-Based Paper Trading

M23 extends scheduled Alpaca paper trading to the remaining non-AI rule-based
strategies while preserving the existing paper-only safety boundary.

## Scope

Supported paper trading configurations:

- `PAPER_TRADING` + `BUY_AND_HOLD` + `DAILY` + supported equity allowlist
- `PAPER_TRADING` + `MOVING_AVERAGE` + `DAILY` + supported equity allowlist
- `PAPER_TRADING` + `OPENING_RANGE_BREAKOUT` + `INTRADAY_5_MIN` + supported equity allowlist
- gated diagnostics-only `PAPER_TRADING_SMOKE_TEST` + `TEST_1_MIN` + `SPY`

Out of scope:

- `AGENTIC_AI` paper trading
- real LLM providers
- real-money trading
- non-SPY assets
- European ETF/Xetra support
- account/position reconciliation
- automatic order cancellation
- outbox processing
- frontend order action buttons

## Moving Average Paper Trading

Moving Average paper trading is supported for both scheduled execution and
manual `run-next-step` debugging.

The strategy uses the latest completed daily bar close and loads a lookback
buffer before the evaluated bar so the configured moving average window can be
computed without creating historical execution artifacts.

If there are not enough daily bars for the configured window, the step persists
a safe `HOLD` decision with diagnostic raw decision details. No broker order is
submitted.

## Opening Range Breakout Paper Trading

Opening Range Breakout paper trading is scheduled-only in M23.

The paper scheduler evaluates only completed 5-minute regular-session bars. It
uses the US equities trading calendar, including early-close sessions. Missed
intraday slots are not backfilled.

If the expected completed bar is not available from the intraday provider, the
scheduler skips before creating an `ExecutionStep`. No artifacts, orders, or
trades are created for that unavailable bar.

ORB keeps the historical rule of at most one completed round trip per session.
End-of-day exits use the calendar final expected bar, including early closes.

## Safety

Every rule-based paper strategy still follows:

```text
Strategy -> TradingDecision -> RiskCheck -> ExecutionStep -> Order/Trade
```

Broker submission happens only after a persisted approved `RiskCheck`.

`HOLD` and rejected risk checks create no broker call. `SELL` can only close the
local long SPY position and must never open a short position. BUY sizing uses
available cash and whole-share rounding in the RiskCheck path.

Submitted paper orders continue to be synced by the existing M20 broker-sync
job. Broker sync also continues for open submitted orders after pause or stop.

## Paper Status

The paper-status endpoint reports the new rule-based configurations as scheduler
supported. ORB status includes structured operational metadata with current or
next due bar timestamps for debugging, while preserving concise reason codes for
UI display.
