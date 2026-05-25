from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.enums import TradeAction


@dataclass(frozen=True)
class OpeningRangeBreakoutState:
    session_date: date
    opening_range_high: Decimal | None
    opening_range_low: Decimal | None
    opening_range_complete: bool
    final_bar: bool
    round_trip_completed: bool


@dataclass(frozen=True)
class OpeningRangeBreakoutDecision:
    action: TradeAction
    symbol: str
    reason: str
    raw_decision_json: dict


class OpeningRangeBreakoutStrategy:
    source_name = "OpeningRangeBreakoutStrategy"

    def decide(
        self,
        *,
        symbol: str,
        close: Decimal,
        position_quantity: Decimal | None,
        state: OpeningRangeBreakoutState,
    ) -> OpeningRangeBreakoutDecision:
        has_position = position_quantity is not None and position_quantity > 0
        base_raw = {
            "strategy": self.source_name,
            "sessionDate": state.session_date.isoformat(),
            "openingRangeHigh": float(state.opening_range_high)
            if state.opening_range_high is not None
            else None,
            "openingRangeLow": float(state.opening_range_low)
            if state.opening_range_low is not None
            else None,
            "openingRangeComplete": state.opening_range_complete,
            "roundTripCompleted": state.round_trip_completed,
            "eodExit": False,
            "breakoutDirection": None,
        }

        if not state.opening_range_complete:
            return OpeningRangeBreakoutDecision(
                action=TradeAction.HOLD,
                symbol=symbol,
                reason="Opening range is not complete yet.",
                raw_decision_json=base_raw,
            )

        if state.final_bar and has_position:
            raw = {**base_raw, "eodExit": True}
            return OpeningRangeBreakoutDecision(
                action=TradeAction.SELL,
                symbol=symbol,
                reason="Final regular-session bar exits the open long position.",
                raw_decision_json=raw,
            )

        if state.round_trip_completed:
            return OpeningRangeBreakoutDecision(
                action=TradeAction.HOLD,
                symbol=symbol,
                reason="Session already completed one round trip; re-entry is disabled.",
                raw_decision_json=base_raw,
            )

        if state.opening_range_high is not None and close > state.opening_range_high:
            if not has_position:
                raw = {**base_raw, "breakoutDirection": "UP"}
                return OpeningRangeBreakoutDecision(
                    action=TradeAction.BUY,
                    symbol=symbol,
                    reason="Close broke above the opening range high with no position.",
                    raw_decision_json=raw,
                )
            return OpeningRangeBreakoutDecision(
                action=TradeAction.HOLD,
                symbol=symbol,
                reason="Close is above the opening range high and position is already held.",
                raw_decision_json=base_raw,
            )

        if state.opening_range_low is not None and close < state.opening_range_low:
            if has_position:
                raw = {**base_raw, "breakoutDirection": "DOWN"}
                return OpeningRangeBreakoutDecision(
                    action=TradeAction.SELL,
                    symbol=symbol,
                    reason="Close broke below the opening range low with an open position.",
                    raw_decision_json=raw,
                )
            return OpeningRangeBreakoutDecision(
                action=TradeAction.HOLD,
                symbol=symbol,
                reason="Close is below the opening range low with no position.",
                raw_decision_json=base_raw,
            )

        return OpeningRangeBreakoutDecision(
            action=TradeAction.HOLD,
            symbol=symbol,
            reason="No opening range breakout signal is present.",
            raw_decision_json=base_raw,
        )
