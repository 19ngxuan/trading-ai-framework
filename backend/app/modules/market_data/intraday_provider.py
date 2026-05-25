from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Protocol
from zoneinfo import ZoneInfo

from app.domain.enums import TradingFrequency


NEW_YORK_TZ = ZoneInfo("America/New_York")
REGULAR_SESSION_START = time(9, 30)
REGULAR_SESSION_FINAL_BAR = time(15, 55)
REGULAR_SESSION_END = time(16, 0)
OPENING_RANGE_END = time(9, 55)
BAR_INTERVAL = timedelta(minutes=5)
EXPECTED_BARS_PER_SESSION = 78


@dataclass(frozen=True)
class IntradayBar:
    timestamp: datetime
    session_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    raw: dict


class IntradayMarketDataProvider(Protocol):
    def load_range(
        self,
        start_date: date,
        end_date: date,
        symbol: str = "SPY",
        frequency: TradingFrequency = TradingFrequency.INTRADAY_5_MIN,
    ) -> list[IntradayBar]:
        ...


def expected_session_timestamps(session_date: date) -> list[datetime]:
    current = datetime.combine(session_date, REGULAR_SESSION_START)
    final = datetime.combine(session_date, REGULAR_SESSION_FINAL_BAR)
    timestamps: list[datetime] = []
    while current <= final:
        timestamps.append(current)
        current += BAR_INTERVAL
    return timestamps


def is_regular_session_bar(timestamp: datetime) -> bool:
    if timestamp.second != 0 or timestamp.microsecond != 0:
        return False
    if timestamp.time() < REGULAR_SESSION_START:
        return False
    if timestamp.time() > REGULAR_SESSION_FINAL_BAR:
        return False
    minutes_since_midnight = timestamp.hour * 60 + timestamp.minute
    session_start_minutes = REGULAR_SESSION_START.hour * 60 + REGULAR_SESSION_START.minute
    return (minutes_since_midnight - session_start_minutes) % 5 == 0
