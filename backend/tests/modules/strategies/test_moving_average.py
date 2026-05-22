from decimal import Decimal

from app.domain.enums import TradeAction
from app.modules.strategies.moving_average import MovingAverageStrategy


def test_moving_average_unavailable_returns_hold() -> None:
    decision = MovingAverageStrategy().decide(
        symbol="SPY",
        price=Decimal("100"),
        moving_average=None,
        position_quantity=Decimal("0"),
        window=3,
    )

    assert decision.action is TradeAction.HOLD
    assert "unavailable" in decision.reason


def test_price_above_average_without_position_returns_buy() -> None:
    decision = MovingAverageStrategy().decide(
        symbol="SPY",
        price=Decimal("101"),
        moving_average=Decimal("100"),
        position_quantity=Decimal("0"),
    )

    assert decision.action is TradeAction.BUY


def test_price_above_average_with_position_returns_hold() -> None:
    decision = MovingAverageStrategy().decide(
        symbol="SPY",
        price=Decimal("101"),
        moving_average=Decimal("100"),
        position_quantity=Decimal("5"),
    )

    assert decision.action is TradeAction.HOLD


def test_price_below_average_with_position_returns_sell() -> None:
    decision = MovingAverageStrategy().decide(
        symbol="SPY",
        price=Decimal("99"),
        moving_average=Decimal("100"),
        position_quantity=Decimal("5"),
    )

    assert decision.action is TradeAction.SELL


def test_price_below_average_without_position_returns_hold() -> None:
    decision = MovingAverageStrategy().decide(
        symbol="SPY",
        price=Decimal("99"),
        moving_average=Decimal("100"),
        position_quantity=Decimal("0"),
    )

    assert decision.action is TradeAction.HOLD


def test_price_equal_average_returns_hold() -> None:
    decision = MovingAverageStrategy().decide(
        symbol="SPY",
        price=Decimal("100"),
        moving_average=Decimal("100"),
        position_quantity=Decimal("5"),
    )

    assert decision.action is TradeAction.HOLD
