from datetime import date

import pytest

from app.domain.enums import TradingFrequency
from app.modules.market_data.errors import (
    MarketDataProviderError,
    MarketDataUnavailableError,
)
from app.modules.market_data.intraday_csv_loader import (
    EXPECTED_BARS_PER_SESSION,
    SpyIntradayCsvLoader,
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
