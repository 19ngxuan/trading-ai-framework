from decimal import Decimal

import pytest

from app.domain.enums import TradeAction
from app.modules.agents.output_parser import AgentOutputParseError, AgentOutputParser


def test_parser_accepts_valid_actions() -> None:
    parser = AgentOutputParser()

    buy = parser.parse(
        '{"action": "BUY", "confidence": 0.75, "rationale": "Buy rationale."}'
    )
    hold = parser.parse(
        '{"action": "HOLD", "confidence": 0, "rationale": "Hold rationale."}'
    )
    sell = parser.parse(
        '{"action": "SELL", "confidence": 1, "rationale": "Sell rationale."}'
    )

    assert buy.action is TradeAction.BUY
    assert buy.confidence == Decimal("0.7500")
    assert hold.action is TradeAction.HOLD
    assert sell.action is TradeAction.SELL


@pytest.mark.parametrize(
    "raw_output",
    [
        "not json",
        "[]",
        '{"action": "WAIT", "confidence": 0.5, "rationale": "bad action"}',
        '{"action": "BUY", "confidence": 2, "rationale": "bad confidence"}',
        '{"action": "BUY", "confidence": 0.5, "rationale": ""}',
    ],
)
def test_parser_rejects_invalid_output(raw_output: str) -> None:
    with pytest.raises(AgentOutputParseError):
        AgentOutputParser().parse(raw_output)
