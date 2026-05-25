from collections import Counter
from datetime import date, datetime

from app.modules.market_data.errors import (
    MarketDataProviderError,
    MarketDataUnavailableError,
)
from app.modules.market_data.intraday_provider import IntradayBar
from app.modules.market_data.trading_calendar import TradingSession


def validate_intraday_bars(
    *,
    bars: list[IntradayBar],
    sessions: list[TradingSession],
    symbol: str,
    provider: str,
) -> list[IntradayBar]:
    if not sessions:
        return []

    expected_by_timestamp: dict[datetime, TradingSession] = {}
    for session in sessions:
        for timestamp in session.expected_bar_start_times:
            expected_by_timestamp[timestamp] = session

    expected_timestamps = set(expected_by_timestamp)
    filtered = [bar for bar in bars if bar.timestamp in expected_timestamps]

    counts = Counter(bar.timestamp for bar in filtered)
    duplicate = next((timestamp for timestamp, count in counts.items() if count > 1), None)
    if duplicate is not None:
        raise MarketDataProviderError(
            f"{provider} returned duplicate intraday bars.",
            details={
                "provider": provider,
                "symbol": symbol,
                "timestamp": duplicate.isoformat(),
            },
        )

    actual_timestamps = set(counts)
    missing = sorted(expected_timestamps - actual_timestamps)
    if missing:
        first_missing = missing[0]
        session = expected_by_timestamp[first_missing]
        actual_for_session = sum(
            1
            for timestamp in actual_timestamps
            if timestamp.date() == session.session_date
        )
        raise MarketDataUnavailableError(
            f"{provider} intraday session is incomplete.",
            details=_session_details(
                provider=provider,
                symbol=symbol,
                session=session,
                actual_bars=actual_for_session,
                missing=missing,
            ),
        )

    return sorted(filtered, key=lambda bar: bar.timestamp)


def _session_details(
    *,
    provider: str,
    symbol: str,
    session: TradingSession,
    actual_bars: int,
    missing: list[datetime],
) -> dict:
    return {
        "provider": provider,
        "symbol": symbol,
        "sessionDate": session.session_date.isoformat(),
        "expectedBars": len(session.expected_bar_start_times),
        "actualBars": actual_bars,
        "missingTimestamps": [timestamp.isoformat() for timestamp in missing[:5]],
        "isEarlyClose": session.is_early_close,
        "sessionOpen": _session_datetime(session.session_date, session.open_time),
        "sessionClose": _session_datetime(session.session_date, session.close_time),
    }


def _session_datetime(session_date: date, value) -> str:
    return datetime.combine(session_date, value).isoformat()
