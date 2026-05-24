from decimal import Decimal

import pytest

from app.domain.enums import FinalAction, TradeAction
from app.modules.execution.position_sizing import (
    PositionSizingConfigurationError,
    calculate_position_size,
    validate_position_sizing_config,
)


def _calculate(
    action: TradeAction = TradeAction.BUY,
    *,
    cash: Decimal = Decimal("10000"),
    current_portfolio_value: Decimal = Decimal("10000"),
    current_position_quantity: Decimal = Decimal("0"),
    price: Decimal = Decimal("471"),
    sizing_type: str | None = "ALL_IN",
    sizing_value: Decimal | None = None,
):
    return calculate_position_size(
        action=action,
        cash=cash,
        current_portfolio_value=current_portfolio_value,
        current_position_quantity=current_position_quantity,
        price=price,
        sizing_type=sizing_type,
        sizing_value=sizing_value,
    )


def test_all_in_uses_available_cash() -> None:
    result = _calculate()

    assert result.final_action is FinalAction.BUY
    assert result.final_quantity == Decimal("21")
    assert result.requested_quantity == Decimal("21")
    assert result.sizing_reason == "ALL_IN"


def test_fixed_cash_caps_buy_notional() -> None:
    result = _calculate(sizing_type="FIXED_CASH", sizing_value=Decimal("1000"))

    assert result.final_action is FinalAction.BUY
    assert result.final_quantity == Decimal("2")
    assert result.requested_quantity == Decimal("2")


def test_percent_of_portfolio_uses_current_portfolio_value() -> None:
    result = _calculate(
        current_portfolio_value=Decimal("20000"),
        sizing_type="PERCENT_OF_PORTFOLIO",
        sizing_value=Decimal("0.10"),
    )

    assert result.final_quantity == Decimal("4")
    assert result.requested_quantity == Decimal("4")


def test_fixed_quantity_caps_to_affordable_whole_shares() -> None:
    result = _calculate(sizing_type="FIXED_QUANTITY", sizing_value=Decimal("5"))

    assert result.final_quantity == Decimal("5")
    assert result.requested_quantity == Decimal("5")

    capped = _calculate(
        cash=Decimal("1000"),
        sizing_type="FIXED_QUANTITY",
        sizing_value=Decimal("5"),
    )
    assert capped.final_quantity == Decimal("2")
    assert capped.requested_quantity == Decimal("5")


def test_buy_below_one_share_becomes_hold() -> None:
    result = _calculate(cash=Decimal("100"))

    assert result.final_action is FinalAction.HOLD
    assert result.final_quantity is None
    assert result.sizing_reason == "POSITION_SIZE_BELOW_ONE_SHARE"


def test_sell_liquidates_existing_long_and_never_shorts() -> None:
    result = _calculate(
        TradeAction.SELL,
        current_position_quantity=Decimal("3"),
    )
    assert result.final_action is FinalAction.SELL
    assert result.final_quantity == Decimal("3")

    no_position = _calculate(TradeAction.SELL)
    assert no_position.final_action is FinalAction.HOLD
    assert no_position.final_quantity is None
    assert no_position.sizing_reason == "NO_POSITION_TO_SELL"


@pytest.mark.parametrize(
    ("sizing_type", "sizing_value"),
    [
        ("FIXED_CASH", Decimal("0")),
        ("PERCENT_OF_PORTFOLIO", Decimal("0")),
        ("PERCENT_OF_PORTFOLIO", Decimal("1.1")),
        ("FIXED_QUANTITY", Decimal("0")),
        ("FIXED_QUANTITY", Decimal("5.5")),
        ("UNKNOWN", Decimal("1")),
    ],
)
def test_invalid_position_sizing_config_is_rejected(
    sizing_type: str,
    sizing_value: Decimal,
) -> None:
    with pytest.raises(PositionSizingConfigurationError):
        validate_position_sizing_config(sizing_type, sizing_value)
