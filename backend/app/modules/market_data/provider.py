from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from app.domain.enums import TradingFrequency


@dataclass(frozen=True)
class DailyBar:
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal
    volume: Decimal
    raw: dict


class MarketDataProvider(Protocol):
    def load_range(
        self,
        start_date: date,
        end_date: date,
        symbol: str = "SPY",
        frequency: TradingFrequency = TradingFrequency.DAILY,
    ) -> list[DailyBar]:
        ...

    def get_latest_bar(self, symbol: str = "SPY") -> DailyBar:
        ...
