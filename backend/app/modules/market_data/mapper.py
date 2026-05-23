from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.modules.market_data.errors import MarketDataProviderError
from app.modules.market_data.provider import DailyBar


def alpaca_bar_to_daily_bar(
    payload: dict[str, Any],
    *,
    symbol: str,
    provider_metadata: dict[str, Any],
) -> DailyBar:
    try:
        timestamp = payload["t"]
        bar_date = _parse_bar_date(timestamp)
        close = Decimal(str(payload["c"]))
        return DailyBar(
            date=bar_date,
            open=Decimal(str(payload["o"])),
            high=Decimal(str(payload["h"])),
            low=Decimal(str(payload["l"])),
            close=close,
            adjusted_close=close,
            volume=Decimal(str(payload["v"])),
            raw={
                "provider": "alpaca",
                "symbol": symbol,
                "metadata": provider_metadata,
                "payload": payload,
            },
        )
    except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
        raise MarketDataProviderError(
            "Alpaca market data response could not be mapped.",
            details={"payload": payload, "error": str(exc)},
        ) from exc


def _parse_bar_date(value: str) -> date:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).date()
