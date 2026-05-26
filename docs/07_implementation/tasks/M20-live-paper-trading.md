# M20 Live Paper Trading Scheduler And Broker Sync

M20 adds backend-only scheduled Alpaca paper trading for
`PAPER_TRADING` + `BUY_AND_HOLD` + `DAILY` + `SPY`.

Scope:

- paper scheduler is disabled by default
- `/start` remains lifecycle-only and does not submit orders
- scheduled paper steps run only for eligible `RUNNING` experiments
- `PAUSED`, `STOPPED`, `FAILED`, and `COMPLETED` experiments receive no new paper trading steps
- submitted paper orders continue to be synced until terminal broker status, including for paused or stopped experiments
- broker sync updates local order status and creates trades only for confirmed filled quantity
- no real-money Alpaca URL is accepted

Out of scope:

- Moving Average paper trading
- Opening Range Breakout paper trading
- Agentic-AI paper trading
- account/position reconciliation
- outbox processing
- automatic broker order cancellation
- frontend feature expansion
- schema migration

Configuration:

```env
PAPER_TRADING_SCHEDULER_ENABLED=false
PAPER_TRADING_SCHEDULER_INTERVAL_SECONDS=60
PAPER_TRADING_SCHEDULER_JOB_ID=paper_trading_scheduler
PAPER_TRADING_DAILY_EVALUATION_TIME=15:55
```

`PAPER_TRADING_DAILY_EVALUATION_TIME` is interpreted in America/New_York. M20
does not backfill missed days.
