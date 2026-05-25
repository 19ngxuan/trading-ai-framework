from datetime import date
from decimal import Decimal

from app.domain.enums import TradeAction
from app.modules.strategies.opening_range_breakout import (
    OpeningRangeBreakoutState,
    OpeningRangeBreakoutStrategy,
)


def _state(
    *,
    complete: bool = True,
    final_bar: bool = False,
    round_trip_completed: bool = False,
) -> OpeningRangeBreakoutState:
    return OpeningRangeBreakoutState(
        session_date=date(2024, 1, 2),
        opening_range_high=Decimal("101"),
        opening_range_low=Decimal("99"),
        opening_range_complete=complete,
        final_bar=final_bar,
        round_trip_completed=round_trip_completed,
    )


def test_opening_range_incomplete_holds() -> None:
    decision = OpeningRangeBreakoutStrategy().decide(
        symbol="SPY",
        close=Decimal("102"),
        position_quantity=Decimal("0"),
        state=_state(complete=False),
    )

    assert decision.action is TradeAction.HOLD


def test_breakout_above_range_buys_without_position() -> None:
    decision = OpeningRangeBreakoutStrategy().decide(
        symbol="SPY",
        close=Decimal("101.01"),
        position_quantity=Decimal("0"),
        state=_state(),
    )

    assert decision.action is TradeAction.BUY
    assert decision.raw_decision_json["breakoutDirection"] == "UP"


def test_breakout_above_range_holds_when_already_holding() -> None:
    decision = OpeningRangeBreakoutStrategy().decide(
        symbol="SPY",
        close=Decimal("101.01"),
        position_quantity=Decimal("5"),
        state=_state(),
    )

    assert decision.action is TradeAction.HOLD


def test_breakdown_below_range_sells_only_when_holding() -> None:
    strategy = OpeningRangeBreakoutStrategy()

    sell_decision = strategy.decide(
        symbol="SPY",
        close=Decimal("98.99"),
        position_quantity=Decimal("5"),
        state=_state(),
    )
    hold_decision = strategy.decide(
        symbol="SPY",
        close=Decimal("98.99"),
        position_quantity=Decimal("0"),
        state=_state(),
    )

    assert sell_decision.action is TradeAction.SELL
    assert sell_decision.raw_decision_json["breakoutDirection"] == "DOWN"
    assert hold_decision.action is TradeAction.HOLD


def test_final_bar_exits_open_position() -> None:
    decision = OpeningRangeBreakoutStrategy().decide(
        symbol="SPY",
        close=Decimal("100"),
        position_quantity=Decimal("5"),
        state=_state(final_bar=True),
    )

    assert decision.action is TradeAction.SELL
    assert decision.raw_decision_json["eodExit"] is True


def test_no_reentry_after_completed_round_trip() -> None:
    decision = OpeningRangeBreakoutStrategy().decide(
        symbol="SPY",
        close=Decimal("102"),
        position_quantity=Decimal("0"),
        state=_state(round_trip_completed=True),
    )

    assert decision.action is TradeAction.HOLD
