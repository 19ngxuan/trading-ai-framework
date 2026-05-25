from datetime import UTC, date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app.domain.enums import TradingFrequency
from app.modules.market_data.errors import (
    MarketDataProviderError,
    MarketDataUnavailableError,
)
from app.modules.market_data.intraday_csv_loader import (
    SpyIntradayCsvLoader,
)
from app.modules.market_data.intraday_provider import EXPECTED_BARS_PER_SESSION
from app.modules.market_data.trading_calendar import (
    StaticTradingCalendar,
    TradingSession,
    expected_bar_start_times,
)

NEW_YORK_TZ = ZoneInfo("America/New_York")


def _session(session_date: date, close_time: time) -> TradingSession:
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


def _csv_row(local_timestamp: datetime, close: str = "100.00") -> str:
    timestamp = (
        local_timestamp.replace(tzinfo=NEW_YORK_TZ)
        .astimezone(UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )
    close_decimal = Decimal(close)
    return (
        f"{timestamp},{close_decimal - Decimal('0.05')},"
        f"{close_decimal + Decimal('0.20')},{close_decimal - Decimal('0.20')},"
        f"{close},1000"
    )


def test_intraday_csv_loader_parses_sorted_new_york_session_bars() -> None:
    bars = SpyIntradayCsvLoader().load_range(
        date(2024, 1, 2),
        date(2024, 1, 3),
        frequency=TradingFrequency.INTRADAY_5_MIN,
    )

    assert len(bars) == EXPECTED_BARS_PER_SESSION * 2
    assert bars == sorted(bars, key=lambda bar: bar.timestamp)
    assert bars[0].timestamp.isoformat() == "2024-01-02T09:30:00"
    assert bars[-1].timestamp.isoformat() == "2024-01-03T15:55:00"
    assert bars[0].timestamp.tzinfo is None
    assert bars[0].raw["timezone"] == "America/New_York"
    assert bars[0].raw["row"]["timestamp"] == "2024-01-02T09:30:00-05:00"


def test_intraday_csv_loader_filters_date_range_inclusively() -> None:
    bars = SpyIntradayCsvLoader().load_range(
        date(2024, 1, 3),
        date(2024, 1, 3),
        frequency=TradingFrequency.INTRADAY_5_MIN,
    )

    assert len(bars) == EXPECTED_BARS_PER_SESSION
    assert {bar.session_date for bar in bars} == {date(2024, 1, 3)}


def test_intraday_csv_loader_rejects_unsupported_frequency() -> None:
    with pytest.raises(MarketDataProviderError):
        SpyIntradayCsvLoader().load_range(
            date(2024, 1, 2),
            date(2024, 1, 2),
            frequency=TradingFrequency.DAILY,
        )


def test_intraday_csv_loader_rejects_missing_session_bars(tmp_path) -> None:
    csv_path = tmp_path / "missing.csv"
    csv_path.write_text(
        "\n".join(
            [
                "timestamp,open,high,low,close,volume",
                "2024-01-02T09:30:00-05:00,100,101,99,100,1000",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(MarketDataUnavailableError):
        SpyIntradayCsvLoader(csv_path).load_range(
            date(2024, 1, 2),
            date(2024, 1, 2),
            frequency=TradingFrequency.INTRADAY_5_MIN,
        )


def test_intraday_csv_loader_rejects_duplicate_timestamps(tmp_path) -> None:
    csv_path = tmp_path / "duplicates.csv"
    row = "2024-01-02T09:30:00-05:00,100,101,99,100,1000"
    csv_path.write_text(
        "\n".join(
            [
                "timestamp,open,high,low,close,volume",
                row,
                row,
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(MarketDataProviderError):
        SpyIntradayCsvLoader(csv_path).load_range(
            date(2024, 1, 2),
            date(2024, 1, 2),
            frequency=TradingFrequency.INTRADAY_5_MIN,
        )


def test_intraday_csv_loader_accepts_early_close_session(tmp_path) -> None:
    csv_path = tmp_path / "early_close.csv"
    session = _session(date(2024, 7, 3), time(13, 0))
    csv_path.write_text(
        "\n".join(
            [
                "timestamp,open,high,low,close,volume",
                *[_csv_row(timestamp) for timestamp in session.expected_bar_start_times],
            ]
        ),
        encoding="utf-8",
    )

    bars = SpyIntradayCsvLoader(
        csv_path,
        trading_calendar=StaticTradingCalendar([session]),
    ).load_range(date(2024, 7, 3), date(2024, 7, 3))

    assert len(bars) == 42
    assert bars[-1].timestamp.isoformat() == "2024-07-03T12:55:00"


def test_intraday_csv_loader_ignores_non_trading_day_rows(tmp_path) -> None:
    csv_path = tmp_path / "non_trading.csv"
    csv_path.write_text(
        "\n".join(
            [
                "timestamp,open,high,low,close,volume",
                _csv_row(datetime(2024, 1, 6, 9, 30)),
            ]
        ),
        encoding="utf-8",
    )

    bars = SpyIntradayCsvLoader(
        csv_path,
        trading_calendar=StaticTradingCalendar([]),
    ).load_range(date(2024, 1, 6), date(2024, 1, 6))

    assert bars == []
