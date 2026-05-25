# M16 Opening Range Breakout Historical Simulation

## Scope

M16 implements deterministic backend-first Opening Range Breakout historical
simulation for:

- `strategyType = OPENING_RANGE_BREAKOUT`
- `mode = HISTORICAL_SIMULATION`
- `tradingFrequency = INTRADAY_5_MIN`
- `assetSymbol = SPY`

M16 uses local SPY 5-minute CSV fixture data only. It does not add an Alpaca
intraday provider, paper-trading ORB, scheduler-triggered ORB, manual ORB
`run-next-step`, broker behavior, agent behavior, real-time data, or real-money
trading.

## Strategy Rules

The regular session is 09:30-16:00 America/New_York, with timestamps interpreted
as five-minute bar starts. The opening range is the first 30 minutes:

- 09:30
- 09:35
- 09:40
- 09:45
- 09:50
- 09:55

After the opening range is complete:

- close above opening range high and no position -> `BUY`
- close below opening range low and holding SPY -> `SELL`
- final regular-session bar and holding SPY -> `SELL`
- otherwise -> `HOLD`

M16 allows at most one completed round trip per session. `SELL` only closes an
existing long SPY position and never opens a short.

## Data And Execution

Fixture location:

```text
backend/app/modules/market_data/fixtures/spy_5min.csv
```

The loader requires complete regular-session five-minute bars for every included
session. Missing bars are fatal. There is no forward-fill or interpolation.

`/start` runs ORB historical simulations to completion. Manual `run-next-step`
and scheduler-triggered ORB are deferred.

The execution pipeline remains:

```text
Strategy -> TradingDecision -> RiskCheck -> ExecutionStep -> Order/Trade
```

Existing configurable position sizing applies to `BUY`. `SELL` remains full
liquidation of the existing long SPY position.
