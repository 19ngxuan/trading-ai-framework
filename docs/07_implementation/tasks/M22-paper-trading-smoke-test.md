# M22 Paper Trading Smoke-Test Strategy

M22 adds a disabled-by-default diagnostics strategy for Alpaca paper trading.

`PAPER_TRADING_SMOKE_TEST` is not an investment strategy. It exists so
developers can verify the scheduled paper trading pipeline, broker order
submission, broker sync, orders/trades persistence, portfolio updates, and M21
operations UI.

## Scope

Supported only when `PAPER_TRADING_TEST_MODE_ENABLED=true`:

- `PAPER_TRADING`
- `PAPER_TRADING_SMOKE_TEST`
- `TEST_1_MIN`
- `SPY`
- scheduled execution only
- US regular market hours only
- fixed 1-share BUY when no local SPY position exists
- SELL only to close the existing local SPY position

Out of scope:

- manual `run-next-step`
- historical simulation
- real-money trading
- agent/LLM logic
- Opening Range Breakout paper trading
- Moving Average paper trading
- broker reconciliation, account sync, position sync, order cancellation

## Safety

The smoke-test strategy is hidden from `/options` and rejected by create
validation unless `PAPER_TRADING_TEST_MODE_ENABLED=true`.

Actual broker submission still requires the existing Alpaca paper-trading safety
configuration, including `ALPACA_PAPER_TRADING_ENABLED=true` and the paper-only
Alpaca trading base URL.

Every smoke-test action still flows through:

`TradingDecision -> RiskCheck -> ExecutionStep -> Order/Trade`

The strategy cannot short and cannot bypass RiskCheck.
