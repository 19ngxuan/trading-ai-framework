from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Protocol

from app.modules.market_data.intraday_provider import BAR_INTERVAL


REGULAR_OPEN_TIME = time(9, 30)
REGULAR_CLOSE_TIME = time(16, 0)
EARLY_CLOSE_TIME = time(13, 0)


@dataclass(frozen=True)
class TradingSession:
    session_date: date
    open_time: time
    close_time: time
    expected_bar_start_times: list[datetime]
    is_early_close: bool


class TradingCalendar(Protocol):
    def sessions_between(self, start_date: date, end_date: date) -> list[TradingSession]:
        ...


class UsEquitiesTradingCalendar:
    def sessions_between(self, start_date: date, end_date: date) -> list[TradingSession]:
        if start_date > end_date:
            return []
        holidays = self._holidays(start_date.year, end_date.year)
        sessions: list[TradingSession] = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 5 and current not in holidays:
                close_time = (
                    EARLY_CLOSE_TIME
                    if current in self._early_closes(start_date.year, end_date.year)
                    else REGULAR_CLOSE_TIME
                )
                sessions.append(
                    TradingSession(
                        session_date=current,
                        open_time=REGULAR_OPEN_TIME,
                        close_time=close_time,
                        expected_bar_start_times=expected_bar_start_times(
                            current,
                            REGULAR_OPEN_TIME,
                            close_time,
                        ),
                        is_early_close=close_time != REGULAR_CLOSE_TIME,
                    )
                )
            current += timedelta(days=1)
        return sessions

    def _holidays(self, start_year: int, end_year: int) -> set[date]:
        holidays: set[date] = set()
        for year in range(start_year - 1, end_year + 2):
            holidays.update(
                {
                    _observed_fixed_holiday(year, 1, 1),
                    _nth_weekday(year, 1, 0, 3),
                    _nth_weekday(year, 2, 0, 3),
                    _good_friday(year),
                    _last_weekday(year, 5, 0),
                    _observed_fixed_holiday(year, 7, 4),
                    _nth_weekday(year, 9, 0, 1),
                    _nth_weekday(year, 11, 3, 4),
                    _observed_fixed_holiday(year, 12, 25),
                }
            )
            if year >= 2022:
                holidays.add(_observed_fixed_holiday(year, 6, 19))
        return holidays

    def _early_closes(self, start_year: int, end_year: int) -> set[date]:
        early_closes: set[date] = set()
        holidays = self._holidays(start_year, end_year)
        for year in range(start_year - 1, end_year + 2):
            for candidate in (
                date(year, 7, 3),
                date(year, 12, 24),
                _nth_weekday(year, 11, 3, 4) + timedelta(days=1),
            ):
                if candidate.weekday() < 5 and candidate not in holidays:
                    early_closes.add(candidate)
        return early_closes


class StaticTradingCalendar:
    def __init__(self, sessions: list[TradingSession]) -> None:
        self.sessions = sessions

    def sessions_between(self, start_date: date, end_date: date) -> list[TradingSession]:
        return [
            session
            for session in self.sessions
            if start_date <= session.session_date <= end_date
        ]


def expected_bar_start_times(
    session_date: date,
    open_time: time,
    close_time: time,
) -> list[datetime]:
    current = datetime.combine(session_date, open_time)
    close = datetime.combine(session_date, close_time)
    timestamps: list[datetime] = []
    while current < close:
        timestamps.append(current)
        current += BAR_INTERVAL
    return timestamps


def _observed_fixed_holiday(year: int, month: int, day: int) -> date:
    holiday = date(year, month, day)
    if holiday.weekday() == 5:
        return holiday - timedelta(days=1)
    if holiday.weekday() == 6:
        return holiday + timedelta(days=1)
    return holiday


def _nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> date:
    current = date(year, month, 1)
    while current.weekday() != weekday:
        current += timedelta(days=1)
    return current + timedelta(days=7 * (occurrence - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        current = date(year, 12, 31)
    else:
        current = date(year, month + 1, 1) - timedelta(days=1)
    while current.weekday() != weekday:
        current -= timedelta(days=1)
    return current


def _good_friday(year: int) -> date:
    # Anonymous Gregorian algorithm for Easter Sunday, then subtract two days.
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    correction = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * correction) // 451
    month = (h + correction - 7 * m + 114) // 31
    day = ((h + correction - 7 * m + 114) % 31) + 1
    return date(year, month, day) - timedelta(days=2)
