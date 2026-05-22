from decimal import Decimal

from app.domain.enums import TradeAction
from app.modules.strategies.buy_and_hold import BuyAndHoldStrategy


def test_buy_and_hold_buys_when_position_is_none() -> None:
    decision = BuyAndHoldStrategy().decide("SPY", None)
    assert decision.action is TradeAction.BUY


def test_buy_and_hold_buys_when_position_is_zero() -> None:
    decision = BuyAndHoldStrategy().decide("SPY", Decimal("0"))
    assert decision.action is TradeAction.BUY


def test_buy_and_hold_holds_when_position_exists() -> None:
    decision = BuyAndHoldStrategy().decide("SPY", Decimal("1"))
    assert decision.action is TradeAction.HOLD
