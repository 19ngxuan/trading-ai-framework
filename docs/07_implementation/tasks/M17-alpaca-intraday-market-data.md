# M17 Alpaca Intraday Market Data For Opening Range Breakout

## Scope

M17 adds Alpaca historical 5-minute SPY bars for Opening Range Breakout
historical simulation when `MARKET_DATA_PROVIDER=alpaca`.

Supported execution remains:

- `strategyType = OPENING_RANGE_BREAKOUT`
- `mode = HISTORICAL_SIMULATION`
- `tradingFrequency = INTRADAY_5_MIN`
- `assetSymbol = SPY`
- full historical `/start` only

M17 does not add ORB `run-next-step`, scheduler-triggered ORB, paper-trading
ORB, live streaming, broker changes, agent changes, frontend feature expansion,
or schema changes.

## Provider Selection

- `MARKET_DATA_PROVIDER=csv` uses local `spy_5min.csv` fixture data.
- `MARKET_DATA_PROVIDER=alpaca` uses Alpaca historical `5Min` bars through the
  Market Data Module.

There is no silent fallback to CSV when Alpaca is selected.

## Alpaca Behavior

The provider calls:

```http
GET /v2/stocks/SPY/bars
```

with:

- `timeframe=5Min`
- `start`
- `end`
- `adjustment`
- `feed`
- `page_token` when provided by Alpaca

Alpaca timestamps are converted to America/New_York local naive timestamps for
the existing persistence model. The original provider payload and metadata are
preserved in `MarketDataSnapshot.raw_data_json`.

## Data Policy

Only expected US equities session 5-minute bar starts are used. Premarket and
after-hours bars are ignored. M18 adds trading-calendar validation, so full
sessions require 78 bars and 13:00 early-close sessions require 42 bars.

Missing bars, duplicate timestamps, malformed payloads, empty results, and
provider errors are fatal. There is no forward-fill or interpolation.
