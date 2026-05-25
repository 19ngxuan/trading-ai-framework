from datetime import date, time

from app.modules.market_data.trading_calendar import (
    EARLY_CLOSE_TIME,
    REGULAR_CLOSE_TIME,
    StaticTradingCalendar,
    TradingSession,
    UsEquitiesTradingCalendar,
    expected_bar_start_times,
)


def test_expected_bar_start_times_for_regular_and_early_close_sessions() -> None:
    regular = expected_bar_start_times(date(2024, 1, 2), time(9, 30), time(16, 0))
    early = expected_bar_start_times(date(2024, 7, 3), time(9, 30), time(13, 0))

    assert len(regular) == 78
    assert regular[0].isoformat() == "2024-01-02T09:30:00"
    assert regular[-1].isoformat() == "2024-01-02T15:55:00"
    assert len(early) == 42
    assert early[0].isoformat() == "2024-07-03T09:30:00"
    assert early[-1].isoformat() == "2024-07-03T12:55:00"


def test_us_equities_calendar_returns_regular_and_early_close_sessions() -> None:
    calendar = UsEquitiesTradingCalendar()

    regular = calendar.sessions_between(date(2024, 1, 2), date(2024, 1, 2))
    early = calendar.sessions_between(date(2024, 7, 3), date(2024, 7, 3))

    assert len(regular) == 1
    assert regular[0].close_time == REGULAR_CLOSE_TIME
    assert regular[0].is_early_close is False
    assert len(regular[0].expected_bar_start_times) == 78
    assert len(early) == 1
    assert early[0].close_time == EARLY_CLOSE_TIME
    assert early[0].is_early_close is True
    assert len(early[0].expected_bar_start_times) == 42


def test_us_equities_calendar_skips_weekends_and_holidays() -> None:
    calendar = UsEquitiesTradingCalendar()

    assert calendar.sessions_between(date(2024, 1, 6), date(2024, 1, 7)) == []
    assert calendar.sessions_between(date(2024, 1, 1), date(2024, 1, 1)) == []


def test_static_trading_calendar_filters_requested_range() -> None:
    session = TradingSession(
        session_date=date(2024, 1, 2),
        open_time=time(9, 30),
        close_time=time(16, 0),
        expected_bar_start_times=expected_bar_start_times(
            date(2024, 1, 2),
            time(9, 30),
            time(16, 0),
        ),
        is_early_close=False,
    )

    calendar = StaticTradingCalendar([session])

    assert calendar.sessions_between(date(2024, 1, 2), date(2024, 1, 2)) == [session]
    assert calendar.sessions_between(date(2024, 1, 3), date(2024, 1, 3)) == []
