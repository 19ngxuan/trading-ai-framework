# M18 Trading Calendar And Early-Close Support For Intraday ORB

## Scope

M18 adds provider-independent US equities trading-calendar validation for
Opening Range Breakout intraday historical simulation.

Supported execution remains:

- `strategyType = OPENING_RANGE_BREAKOUT`
- `mode = HISTORICAL_SIMULATION`
- `tradingFrequency = INTRADAY_5_MIN`
- `assetSymbol = SPY`
- full historical `/start` only

M18 does not add ORB `run-next-step`, scheduler-triggered ORB, paper-trading
ORB, live streaming, broker changes, agent changes, frontend feature expansion,
or schema changes.

## Calendar Behavior

The calendar returns expected US equities trading sessions for the requested date
range. Weekends and full market holidays return no session.

For each session, expected five-minute bar starts are generated from session open
inclusive to session close exclusive:

- normal 09:30-16:00 session: 09:30 through 15:55 = 78 bars
- 13:00 early close: 09:30 through 12:55 = 42 bars

If the requested date range contains only non-trading days, the ORB experiment
completes successfully with zero execution steps and a normal completion event.

## Validation Policy

CSV and Alpaca intraday providers share the same validation logic.

Provider-specific code only loads and maps raw bars. Shared validation:

- filters to expected calendar session timestamps
- ignores provider bars on non-trading days
- ignores premarket and after-hours bars
- rejects duplicate expected-session timestamps
- fails if any expected timestamp is missing
- returns sorted validated bars

There is no forward-fill, interpolation, or silent CSV fallback when Alpaca is
selected.

## ORB Behavior

The ORB strategy rules are unchanged. The final bar of the trading day is now the
last validated bar for that calendar session, so early-close sessions exit at the
early-close final bar.
