import csv
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.domain.enums import TradingFrequency
from app.modules.market_data.errors import (
    MarketDataProviderError,
    MarketDataUnavailableError,
)
from app.modules.market_data.intraday_provider import (
    EXPECTED_BARS_PER_SESSION,
    NEW_YORK_TZ,
    IntradayBar,
    expected_session_timestamps,
    is_regular_session_bar,
)


class SpyIntradayCsvLoader:
    def __init__(self, csv_path: Path | None = None) -> None:
        self.csv_path = csv_path or Path(__file__).parent / "fixtures" / "spy_5min.csv"

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

        rows = self._read_rows()
        bars = [
            bar
            for bar in rows
            if start_date <= bar.session_date <= end_date
        ]
        if not bars:
            raise MarketDataUnavailableError(
                "No intraday SPY fixture bars are available for the requested range."
            )

        bars.sort(key=lambda bar: bar.timestamp)
        self._validate_no_duplicates(bars)
        self._validate_sessions_complete(bars)
        return bars

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
        if not is_regular_session_bar(local_timestamp):
            raise MarketDataProviderError(
                f"Intraday timestamp at row {row_number} is outside regular session."
            )

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

    def _validate_no_duplicates(self, bars: list[IntradayBar]) -> None:
        seen: set[datetime] = set()
        for bar in bars:
            if bar.timestamp in seen:
                raise MarketDataProviderError(
                    f"Duplicate intraday timestamp: {bar.timestamp.isoformat()}."
                )
            seen.add(bar.timestamp)

    def _validate_sessions_complete(self, bars: list[IntradayBar]) -> None:
        by_session: dict[date, set[datetime]] = defaultdict(set)
        for bar in bars:
            by_session[bar.session_date].add(bar.timestamp)

        for session_date, timestamps in by_session.items():
            expected = set(expected_session_timestamps(session_date))
            missing = sorted(expected - timestamps)
            extra = sorted(timestamps - expected)
            if missing or extra or len(timestamps) != EXPECTED_BARS_PER_SESSION:
                missing_preview = [value.isoformat() for value in missing[:3]]
                extra_preview = [value.isoformat() for value in extra[:3]]
                raise MarketDataUnavailableError(
                    "Intraday SPY fixture session is incomplete.",
                    details={
                        "sessionDate": session_date.isoformat(),
                        "missing": missing_preview,
                        "extra": extra_preview,
                    },
                )
