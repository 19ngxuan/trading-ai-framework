# M28: Supported Equity Assets

## Goal

Expand selected paper-trading paths from SPY-only to a curated US equity
allowlist.

## Supported Assets

```text
SPY, AAPL, MSFT, NVDA, AMZN, META, GOOGL, TSLA
```

## Scope

- Paper Buy-and-Hold, Moving Average, Agentic AI, and Opening Range Breakout may
  use the allowlist where their runtime path supports it.
- Historical CSV simulations remain SPY-only unless fixture coverage is added.
- Smoke-test diagnostics remain SPY-only.
- `/options` must not perform live Alpaca asset discovery.

## Acceptance Criteria

- Unknown symbols are rejected before broker or market-data calls.
- Selected symbols flow consistently through market data, decisions, risk,
  orders, trades, portfolio state, and UI display.
- No schema migration is required.

