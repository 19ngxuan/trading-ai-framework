import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from importlib.resources import files
from pathlib import Path


@dataclass(frozen=True)
class DailyBar:
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal
    volume: Decimal
    raw: dict[str, str]


class SpyCsvLoader:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path

    def load_range(self, start_date: date, end_date: date) -> list[DailyBar]:
        rows = [bar for bar in self._load_all() if start_date <= bar.date <= end_date]
        return sorted(rows, key=lambda bar: bar.date)

    def _load_all(self) -> list[DailyBar]:
        with self._fixture_path().open(newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            return [
                DailyBar(
                    date=date.fromisoformat(row["date"]),
                    open=Decimal(row["open"]),
                    high=Decimal(row["high"]),
                    low=Decimal(row["low"]),
                    close=Decimal(row["close"]),
                    adjusted_close=Decimal(row["adjusted_close"]),
                    volume=Decimal(row["volume"]),
                    raw=dict(row),
                )
                for row in reader
            ]

    def _fixture_path(self) -> Path:
        if self.path is not None:
            return self.path
        return Path(files("app.modules.market_data").joinpath("fixtures/spy_daily.csv"))
