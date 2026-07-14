from datetime import date
from decimal import Decimal

from app.modules.agents.technical_analysis import TechnicalAnalysisService
from app.modules.market_data.provider import DailyBar


def _bar(day: int, close: str, volume: str = "1000") -> DailyBar:
    close_decimal = Decimal(close)
    return DailyBar(
        date=date(2026, 1, day),
        open=close_decimal - Decimal("0.5"),
        high=close_decimal + Decimal("1"),
        low=close_decimal - Decimal("1"),
        close=close_decimal,
        adjusted_close=close_decimal,
        volume=Decimal(volume),
        raw={},
    )


def test_technical_analysis_calculates_core_indicators() -> None:
    bars = [_bar(index, str(100 + index), "1000") for index in range(1, 31)]
    benchmark = [_bar(index, str(100 + index / 2), "1000") for index in range(1, 31)]

    output = TechnicalAnalysisService().analyze(
        price_history=bars,
        benchmark_history=benchmark,
        intraday_history=[],
        volatility_pct=Decimal("1.5"),
    )

    assert output.indicators is not None
    assert output.indicators["macd"]["histogram"] is not None
    assert output.indicators["bollingerBands"]["upper"] is not None
    assert output.indicators["atr"] is not None
    assert output.indicators["supportResistance"]["support"] is not None
    assert output.indicators["benchmarkRelativeStrength"]["relativeReturnPct"] > 0
    assert output.time_horizon_signals is not None
    assert output.time_horizon_signals["shortTerm"] == "BULLISH"


def test_technical_analysis_handles_daily_only_with_limited_history() -> None:
    bars = [_bar(1, "100"), _bar(2, "101")]

    output = TechnicalAnalysisService().analyze(
        price_history=bars,
        benchmark_history=[],
        intraday_history=[],
        volatility_pct=None,
    )

    assert output.indicators is not None
    assert output.indicators["intradaySignal"]["signal"] == "UNAVAILABLE"
    assert output.time_horizon_signals is not None
    assert output.time_horizon_signals["shortTerm"] == "INSUFFICIENT_HISTORY"
