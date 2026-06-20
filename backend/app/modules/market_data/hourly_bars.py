from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.modules.market_data.errors import MarketDataUnavailableError
from app.modules.market_data.intraday_provider import IntradayBar
from app.modules.market_data.provider import DailyBar
from app.modules.market_data.trading_calendar import TradingSession


HOURLY_WINDOW = timedelta(hours=1)
INTRADAY_BAR_COUNT_PER_HOUR = 12


@dataclass(frozen=True)
class HourlyWindow:
    start: datetime
    end: datetime


def hourly_windows_for_session(session: TradingSession) -> list[HourlyWindow]:
    windows: list[HourlyWindow] = []
    expected = session.expected_bar_start_times
    for index in range(0, len(expected), INTRADAY_BAR_COUNT_PER_HOUR):
        chunk = expected[index : index + INTRADAY_BAR_COUNT_PER_HOUR]
        if len(chunk) < INTRADAY_BAR_COUNT_PER_HOUR:
            break
        windows.append(
            HourlyWindow(
                start=chunk[0],
                end=chunk[-1],
            )
        )
    return windows


def latest_completed_hourly_window(
    local_now: datetime,
    session: TradingSession,
) -> HourlyWindow | None:
    completed = [
        window
        for window in hourly_windows_for_session(session)
        if window.end.replace(tzinfo=local_now.tzinfo) + timedelta(minutes=5)
        <= local_now
    ]
    if not completed:
        return None
    return completed[-1]


def aggregate_hourly_bar(
    *,
    session: TradingSession,
    bars: list[IntradayBar],
    window_start: datetime,
    symbol: str = "SPY",
) -> DailyBar:
    window = next(
        (candidate for candidate in hourly_windows_for_session(session) if candidate.start == window_start),
        None,
    )
    if window is None:
        raise MarketDataUnavailableError(
            "Requested hourly paper-trading window is not part of the trading session.",
            details={
                "symbol": symbol,
                "sessionDate": session.session_date.isoformat(),
                "windowStart": window_start.isoformat(),
            },
        )

    window_bars = [
        bar for bar in bars if window.start <= bar.timestamp <= window.end
    ]
    if len(window_bars) != INTRADAY_BAR_COUNT_PER_HOUR:
        raise MarketDataUnavailableError(
            "Expected completed hourly bar is not available yet.",
            details={
                "symbol": symbol,
                "sessionDate": session.session_date.isoformat(),
                "windowStart": window.start.isoformat(),
                "windowEnd": window.end.isoformat(),
                "expectedBarCount": INTRADAY_BAR_COUNT_PER_HOUR,
                "actualBarCount": len(window_bars),
            },
        )

    first = window_bars[0]
    last = window_bars[-1]
    raw_payloads = [bar.raw for bar in window_bars]
    return DailyBar(
        date=first.session_date,
        open=first.open,
        high=max(bar.high for bar in window_bars),
        low=min(bar.low for bar in window_bars),
        close=last.close,
        adjusted_close=last.close,
        volume=sum((bar.volume for bar in window_bars), Decimal("0")),
        raw={
            "provider": "aggregated-intraday",
            "symbol": symbol,
            "windowStart": window.start.isoformat(),
            "windowEnd": window.end.isoformat(),
            "sourceBarCount": len(window_bars),
            "payloads": raw_payloads,
        },
        timestamp=window.start.astimezone(UTC).replace(tzinfo=None)
        if window.start.tzinfo is not None
        else window.start,
    )
