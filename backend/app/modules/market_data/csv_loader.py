import csv
from datetime import date
from decimal import Decimal
from importlib.resources import files
from pathlib import Path

from app.domain.enums import TradingFrequency
from app.modules.market_data.errors import MarketDataProviderError
from app.modules.market_data.provider import DailyBar

SUPPORTED_SYMBOL = "SPY"


class SpyCsvLoader:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path

    def load_range(
        self,
        start_date: date,
        end_date: date,
        symbol: str = SUPPORTED_SYMBOL,
        frequency: TradingFrequency = TradingFrequency.DAILY,
    ) -> list[DailyBar]:
        self._validate_request(symbol, frequency)
        rows = [bar for bar in self._load_all() if start_date <= bar.date <= end_date]
        return sorted(rows, key=lambda bar: bar.date)

    def get_latest_bar(self, symbol: str = SUPPORTED_SYMBOL) -> DailyBar:
        self._validate_request(symbol, TradingFrequency.DAILY)
        rows = self._load_all()
        if not rows:
            raise MarketDataProviderError("CSV market data fixture is empty.")
        return sorted(rows, key=lambda bar: bar.date)[-1]

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

    def _validate_request(self, symbol: str, frequency: TradingFrequency) -> None:
        if symbol != SUPPORTED_SYMBOL:
            raise MarketDataProviderError(
                "CSV market data provider supports SPY only.",
                details={"symbol": symbol},
            )
        if frequency is not TradingFrequency.DAILY:
            raise MarketDataProviderError(
                "CSV market data provider supports daily bars only.",
                details={"frequency": frequency.value},
            )
