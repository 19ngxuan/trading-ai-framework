from datetime import UTC, datetime
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
        parsed_timestamp = _parse_bar_timestamp(timestamp)
        bar_date = parsed_timestamp.date()
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
            timestamp=parsed_timestamp.astimezone(UTC).replace(tzinfo=None),
        )
    except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
        raise MarketDataProviderError(
            "Alpaca market data response could not be mapped.",
            details={"payload": payload, "error": str(exc)},
        ) from exc


def _parse_bar_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)
