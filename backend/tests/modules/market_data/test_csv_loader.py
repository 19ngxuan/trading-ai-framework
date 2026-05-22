from datetime import date
from decimal import Decimal

from app.modules.market_data.csv_loader import SpyCsvLoader


def test_spy_csv_loader_parses_fixture_rows() -> None:
    rows = SpyCsvLoader().load_range(date(2024, 1, 2), date(2024, 1, 2))
    assert len(rows) == 1
    assert rows[0].date == date(2024, 1, 2)
    assert rows[0].adjusted_close == Decimal("471.00")
    assert isinstance(rows[0].volume, Decimal)


def test_spy_csv_loader_filters_inclusive_range_in_ascending_order() -> None:
    rows = SpyCsvLoader().load_range(date(2024, 1, 3), date(2024, 1, 5))
    assert [row.date for row in rows] == [
        date(2024, 1, 3),
        date(2024, 1, 4),
        date(2024, 1, 5),
    ]
