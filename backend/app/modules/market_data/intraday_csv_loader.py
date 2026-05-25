import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.domain.enums import TradingFrequency
from app.modules.market_data.errors import (
    MarketDataProviderError,
    MarketDataUnavailableError,
)
from app.modules.market_data.intraday_provider import (
    NEW_YORK_TZ,
    IntradayBar,
)
from app.modules.market_data.intraday_validation import validate_intraday_bars
from app.modules.market_data.trading_calendar import (
    TradingCalendar,
    UsEquitiesTradingCalendar,
)


class SpyIntradayCsvLoader:
    def __init__(
        self,
        csv_path: Path | None = None,
        trading_calendar: TradingCalendar | None = None,
    ) -> None:
        self.csv_path = csv_path or Path(__file__).parent / "fixtures" / "spy_5min.csv"
        self.trading_calendar = trading_calendar or UsEquitiesTradingCalendar()

    def load_range(
        self,
        start_date: date,
        end_date: date,
        symbol: str = "SPY",
        frequency: TradingFrequency = TradingFrequency.INTRADAY_5_MIN,
    ) -> list[IntradayBar]:
        if symbol != "SPY":
            raise MarketDataProviderError("Only SPY intraday CSV data is supported.")
        if frequency is not TradingFrequency.INTRADAY_5_MIN:
            raise MarketDataProviderError("Only INTRADAY_5_MIN CSV data is supported.")
        if start_date > end_date:
            raise MarketDataProviderError("start_date must be before or equal to end_date.")

        sessions = self.trading_calendar.sessions_between(start_date, end_date)
        rows = self._read_rows()
        candidate_bars = [
            bar
            for bar in rows
            if start_date <= bar.session_date <= end_date
        ]
        if not candidate_bars and sessions:
            raise MarketDataUnavailableError(
                "No intraday SPY fixture bars are available for the requested range."
            )
        return validate_intraday_bars(
            bars=candidate_bars,
            sessions=sessions,
            symbol=symbol,
            provider="csv_intraday",
        )

    def _read_rows(self) -> list[IntradayBar]:
        if not self.csv_path.exists():
            raise MarketDataUnavailableError(
                f"Intraday CSV fixture was not found: {self.csv_path}"
            )

        with self.csv_path.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            required_columns = {"timestamp", "open", "high", "low", "close", "volume"}
            if set(reader.fieldnames or []) != required_columns:
                raise MarketDataProviderError(
                    "Intraday CSV fixture must contain timestamp,open,high,low,close,volume."
                )
            return [self._parse_row(row, row_number=index + 2) for index, row in enumerate(reader)]

    def _parse_row(self, row: dict[str, str], row_number: int) -> IntradayBar:
        try:
            parsed_timestamp = datetime.fromisoformat(row["timestamp"])
        except ValueError as exc:
            raise MarketDataProviderError(
                f"Malformed intraday timestamp at row {row_number}."
            ) from exc
        if parsed_timestamp.tzinfo is None:
            raise MarketDataProviderError(
                f"Intraday timestamp at row {row_number} must include a timezone."
            )

        local_timestamp = parsed_timestamp.astimezone(NEW_YORK_TZ).replace(tzinfo=None)

        try:
            open_price = Decimal(row["open"])
            high_price = Decimal(row["high"])
            low_price = Decimal(row["low"])
            close_price = Decimal(row["close"])
            volume = Decimal(row["volume"])
        except (InvalidOperation, KeyError) as exc:
            raise MarketDataProviderError(
                f"Malformed numeric intraday value at row {row_number}."
            ) from exc

        raw_row = dict(row)
        return IntradayBar(
            timestamp=local_timestamp,
            session_date=local_timestamp.date(),
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            raw={
                "provider": "csv_intraday",
                "timezone": "America/New_York",
                "timestampLocal": local_timestamp.isoformat(),
                "row": raw_row,
            },
        )
