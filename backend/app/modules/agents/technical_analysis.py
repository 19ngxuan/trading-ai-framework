from decimal import Decimal

from app.modules.agents.pipeline_types import MarketBias, TechnicalAnalysisOutput
from app.modules.market_data.intraday_provider import IntradayBar
from app.modules.market_data.provider import DailyBar


class TechnicalAnalysisService:
    def analyze(
        self,
        *,
        price_history: list[DailyBar],
        benchmark_history: list[DailyBar],
        intraday_history: list[IntradayBar],
        volatility_pct: Decimal | None,
    ) -> TechnicalAnalysisOutput:
        closes = [bar.adjusted_close for bar in price_history]
        current_price = closes[-1] if closes else Decimal("0")
        rsi = self._rsi(closes)
        sma_20 = self._sma(closes, 20)
        macd = self._macd(closes)
        bollinger = self._bollinger_bands(closes)
        atr = self._atr(price_history)
        volume = self._volume_analysis(price_history)
        support_resistance = self._support_resistance(price_history)
        candlestick = self._candlestick(price_history)
        horizons = self._time_horizon_signals(price_history)
        intraday = self._intraday_signal(intraday_history)
        relative_strength = self._relative_strength(price_history, benchmark_history)

        signal_score = Decimal("0")
        if rsi is not None:
            if rsi < Decimal("30"):
                signal_score += Decimal("1")
            elif rsi > Decimal("70"):
                signal_score -= Decimal("1")
        if sma_20 is not None:
            signal_score += Decimal("1") if current_price > sma_20 else Decimal("-1")
        if macd["histogram"] is not None:
            signal_score += Decimal("1") if macd["histogram"] > 0 else Decimal("-1")
        if relative_strength["relativeReturnPct"] is not None:
            signal_score += (
                Decimal("1")
                if relative_strength["relativeReturnPct"] > 0
                else Decimal("-1")
            )

        signal = MarketBias.NEUTRAL
        confidence = Decimal("0.5000")
        if signal_score >= Decimal("2"):
            signal = MarketBias.BULLISH
            confidence = Decimal("0.7000")
        elif signal_score <= Decimal("-2"):
            signal = MarketBias.BEARISH
            confidence = Decimal("0.7000")

        trend = "FLAT"
        if sma_20 is not None and current_price > sma_20:
            trend = "UPWARD"
        elif sma_20 is not None and current_price < sma_20:
            trend = "DOWNWARD"

        indicators = {
            "macd": _float_dict(macd),
            "bollingerBands": _float_dict(bollinger),
            "atr": float(atr) if atr is not None else None,
            "volumeAnalysis": volume,
            "supportResistance": _float_dict(support_resistance),
            "candlestickPatterns": candlestick,
            "intradaySignal": intraday,
            "benchmarkRelativeStrength": _float_dict(relative_strength),
        }
        risk_notes = self._risk_notes(atr, current_price, volume, candlestick)
        rationale = (
            f"Technical signal is {signal.value}. Trend is {trend}. "
            f"MACD histogram is {macd['histogram']}. ATR is {atr}. "
            f"Relative strength is {relative_strength['relativeReturnPct']}%."
        )
        return TechnicalAnalysisOutput(
            signal=signal,
            confidence=confidence,
            rationale=rationale,
            rsi=rsi,
            sma_20=sma_20,
            trend=trend,
            volatility_pct=volatility_pct,
            indicators=indicators,
            time_horizon_signals=horizons,
            risk_notes=risk_notes,
        )

    def _sma(self, closes: list[Decimal], window: int) -> Decimal | None:
        if len(closes) < window:
            return None
        selection = closes[-window:]
        return (sum(selection, Decimal("0")) / Decimal(window)).quantize(
            Decimal("0.0001")
        )

    def _ema(self, closes: list[Decimal], window: int) -> Decimal | None:
        if len(closes) < window:
            return None
        multiplier = Decimal("2") / Decimal(window + 1)
        ema = sum(closes[:window], Decimal("0")) / Decimal(window)
        for close in closes[window:]:
            ema = ((close - ema) * multiplier) + ema
        return ema.quantize(Decimal("0.0001"))

    def _rsi(self, closes: list[Decimal], window: int = 14) -> Decimal | None:
        if len(closes) <= window:
            return None
        changes = [current - previous for previous, current in zip(closes, closes[1:])]
        gains = [change for change in changes if change > 0]
        losses = [-change for change in changes if change < 0]
        if not gains and not losses:
            return Decimal("50.0000")
        avg_gain = (
            sum(gains[-window:], Decimal("0")) / Decimal(window)
            if gains
            else Decimal("0")
        )
        avg_loss = (
            sum(losses[-window:], Decimal("0")) / Decimal(window)
            if losses
            else Decimal("0")
        )
        if avg_loss == 0:
            return Decimal("100.0000")
        rs = avg_gain / avg_loss
        return (Decimal("100") - (Decimal("100") / (Decimal("1") + rs))).quantize(
            Decimal("0.0001")
        )

    def _macd(self, closes: list[Decimal]) -> dict[str, Decimal | None]:
        ema_12 = self._ema(closes, 12)
        ema_26 = self._ema(closes, 26)
        if ema_12 is None or ema_26 is None:
            return {"macd": None, "signal": None, "histogram": None}
        macd_line = (ema_12 - ema_26).quantize(Decimal("0.0001"))
        signal = self._ema([macd_line] * 9, 9)
        histogram = (macd_line - signal).quantize(Decimal("0.0001")) if signal else None
        return {"macd": macd_line, "signal": signal, "histogram": histogram}

    def _bollinger_bands(self, closes: list[Decimal]) -> dict[str, Decimal | None]:
        sma = self._sma(closes, 20)
        if sma is None:
            return {"middle": None, "upper": None, "lower": None}
        selection = closes[-20:]
        variance = sum((close - sma) * (close - sma) for close in selection) / Decimal(20)
        stddev = variance.sqrt()
        return {
            "middle": sma,
            "upper": (sma + (stddev * Decimal("2"))).quantize(Decimal("0.0001")),
            "lower": (sma - (stddev * Decimal("2"))).quantize(Decimal("0.0001")),
        }

    def _atr(self, bars: list[DailyBar], window: int = 14) -> Decimal | None:
        if len(bars) <= window:
            return None
        ranges: list[Decimal] = []
        for previous, current in zip(bars, bars[1:]):
            ranges.append(
                max(
                    current.high - current.low,
                    abs(current.high - previous.adjusted_close),
                    abs(current.low - previous.adjusted_close),
                )
            )
        return (sum(ranges[-window:], Decimal("0")) / Decimal(window)).quantize(
            Decimal("0.0001")
        )

    def _volume_analysis(self, bars: list[DailyBar]) -> dict[str, float | str | None]:
        if len(bars) < 20:
            return {"volumeRatio": None, "signal": "INSUFFICIENT_HISTORY"}
        avg_volume = sum((bar.volume for bar in bars[-20:]), Decimal("0")) / Decimal(20)
        current_volume = bars[-1].volume
        ratio = current_volume / avg_volume if avg_volume else Decimal("0")
        signal = "NORMAL"
        if ratio >= Decimal("1.5"):
            signal = "HIGH_VOLUME"
        elif ratio <= Decimal("0.5"):
            signal = "LOW_VOLUME"
        return {"volumeRatio": float(ratio.quantize(Decimal("0.0001"))), "signal": signal}

    def _support_resistance(self, bars: list[DailyBar]) -> dict[str, Decimal | None]:
        if len(bars) < 5:
            return {"support": None, "resistance": None}
        selection = bars[-20:]
        return {
            "support": min(bar.low for bar in selection).quantize(Decimal("0.0001")),
            "resistance": max(bar.high for bar in selection).quantize(Decimal("0.0001")),
        }

    def _candlestick(self, bars: list[DailyBar]) -> list[str]:
        if not bars:
            return []
        bar = bars[-1]
        body = abs(bar.close - bar.open)
        full_range = bar.high - bar.low
        patterns: list[str] = []
        if full_range > 0 and body / full_range < Decimal("0.1"):
            patterns.append("DOJI")
        if bar.close > bar.open and body > full_range * Decimal("0.6"):
            patterns.append("BULLISH_WIDE_BODY")
        if bar.close < bar.open and body > full_range * Decimal("0.6"):
            patterns.append("BEARISH_WIDE_BODY")
        return patterns

    def _time_horizon_signals(self, bars: list[DailyBar]) -> dict[str, str]:
        closes = [bar.adjusted_close for bar in bars]
        return {
            "shortTerm": self._return_signal(closes, 5),
            "mediumTerm": self._return_signal(closes, 20),
            "longTerm": self._return_signal(closes, 60),
        }

    def _return_signal(self, closes: list[Decimal], window: int) -> str:
        if len(closes) <= window:
            return "INSUFFICIENT_HISTORY"
        change = closes[-1] - closes[-window - 1]
        if change > 0:
            return "BULLISH"
        if change < 0:
            return "BEARISH"
        return "NEUTRAL"

    def _intraday_signal(self, bars: list[IntradayBar]) -> dict[str, str | float | None]:
        if len(bars) < 2:
            return {"signal": "UNAVAILABLE", "intradayReturnPct": None}
        first = bars[0].close
        latest = bars[-1].close
        intraday_return = ((latest - first) / first * Decimal("100")) if first else Decimal("0")
        signal = "BULLISH" if intraday_return > 0 else "BEARISH" if intraday_return < 0 else "NEUTRAL"
        return {
            "signal": signal,
            "intradayReturnPct": float(intraday_return.quantize(Decimal("0.0001"))),
        }

    def _relative_strength(
        self, bars: list[DailyBar], benchmark_bars: list[DailyBar]
    ) -> dict[str, Decimal | None]:
        if len(bars) < 2 or len(benchmark_bars) < 2:
            return {"assetReturnPct": None, "benchmarkReturnPct": None, "relativeReturnPct": None}
        asset_return = _return_pct(bars[0].adjusted_close, bars[-1].adjusted_close)
        benchmark_return = _return_pct(
            benchmark_bars[0].adjusted_close, benchmark_bars[-1].adjusted_close
        )
        return {
            "assetReturnPct": asset_return,
            "benchmarkReturnPct": benchmark_return,
            "relativeReturnPct": (asset_return - benchmark_return).quantize(Decimal("0.0001")),
        }

    def _risk_notes(
        self,
        atr: Decimal | None,
        current_price: Decimal,
        volume: dict[str, float | str | None],
        candlestick: list[str],
    ) -> list[str]:
        notes: list[str] = []
        if atr is not None and current_price and atr / current_price > Decimal("0.03"):
            notes.append("ATR is elevated relative to price.")
        if volume.get("signal") == "HIGH_VOLUME":
            notes.append("Current volume is materially above the 20-day average.")
        if "BEARISH_WIDE_BODY" in candlestick:
            notes.append("Latest candle shows bearish wide-body pressure.")
        return notes


def _return_pct(first: Decimal, latest: Decimal) -> Decimal:
    if first == 0:
        return Decimal("0.0000")
    return ((latest - first) / first * Decimal("100")).quantize(Decimal("0.0001"))


def _float_dict(payload: dict) -> dict:
    return {
        key: float(value) if isinstance(value, Decimal) else value
        for key, value in payload.items()
    }
