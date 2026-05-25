from datetime import date, datetime, time
from decimal import Decimal

import pytest

from app.modules.market_data.errors import (
    MarketDataProviderError,
    MarketDataUnavailableError,
)
from app.modules.market_data.intraday_provider import IntradayBar
from app.modules.market_data.intraday_validation import validate_intraday_bars
from app.modules.market_data.trading_calendar import (
    TradingSession,
    expected_bar_start_times,
)


def _session(
    session_date: date,
    close_time: time = time(16, 0),
) -> TradingSession:
    return TradingSession(
        session_date=session_date,
        open_time=time(9, 30),
        close_time=close_time,
        expected_bar_start_times=expected_bar_start_times(
            session_date,
            time(9, 30),
            close_time,
        ),
        is_early_close=close_time != time(16, 0),
    )


def _bar(timestamp: datetime) -> IntradayBar:
    return IntradayBar(
        timestamp=timestamp,
        session_date=timestamp.date(),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=Decimal("1000"),
        raw={"timestamp": timestamp.isoformat()},
    )


def test_validate_intraday_bars_accepts_regular_and_early_close_sessions() -> None:
    regular_session = _session(date(2024, 1, 2))
    early_session = _session(date(2024, 7, 3), time(13, 0))
    bars = [
        *[_bar(timestamp) for timestamp in regular_session.expected_bar_start_times],
        *[_bar(timestamp) for timestamp in early_session.expected_bar_start_times],
    ]

    validated = validate_intraday_bars(
        bars=bars,
        sessions=[regular_session, early_session],
        symbol="SPY",
        provider="test",
    )

    assert len(validated) == 120
    assert validated[0].timestamp.isoformat() == "2024-01-02T09:30:00"
    assert validated[-1].timestamp.isoformat() == "2024-07-03T12:55:00"


def test_validate_intraday_bars_ignores_non_session_bars() -> None:
    session = _session(date(2024, 1, 2))
    bars = [
        _bar(datetime(2024, 1, 1, 9, 30)),
        _bar(datetime(2024, 1, 2, 9, 0)),
        *[_bar(timestamp) for timestamp in session.expected_bar_start_times],
        _bar(datetime(2024, 1, 2, 16, 0)),
    ]

    validated = validate_intraday_bars(
        bars=bars,
        sessions=[session],
        symbol="SPY",
        provider="test",
    )

    assert len(validated) == 78
    assert all(bar.timestamp.date() == date(2024, 1, 2) for bar in validated)


def test_validate_intraday_bars_returns_empty_when_no_sessions() -> None:
    assert (
        validate_intraday_bars(
            bars=[_bar(datetime(2024, 1, 6, 9, 30))],
            sessions=[],
            symbol="SPY",
            provider="test",
        )
        == []
    )


def test_validate_intraday_bars_rejects_missing_expected_bar() -> None:
    session = _session(date(2024, 7, 3), time(13, 0))
    bars = [_bar(timestamp) for timestamp in session.expected_bar_start_times[1:]]

    with pytest.raises(MarketDataUnavailableError) as exc_info:
        validate_intraday_bars(
            bars=bars,
            sessions=[session],
            symbol="SPY",
            provider="test",
        )

    assert exc_info.value.details["expectedBars"] == 42
    assert exc_info.value.details["actualBars"] == 41
    assert exc_info.value.details["isEarlyClose"] is True


def test_validate_intraday_bars_rejects_duplicate_expected_timestamp() -> None:
    session = _session(date(2024, 1, 2))
    bars = [_bar(timestamp) for timestamp in session.expected_bar_start_times]
    bars.append(_bar(session.expected_bar_start_times[0]))

    with pytest.raises(MarketDataProviderError, match="duplicate"):
        validate_intraday_bars(
            bars=bars,
            sessions=[session],
            symbol="SPY",
            provider="test",
        )
