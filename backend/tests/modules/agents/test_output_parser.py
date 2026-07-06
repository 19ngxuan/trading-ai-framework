from decimal import Decimal

import pytest

from app.domain.enums import PrimaryDriver, TradeAction, TradeIntent
from app.modules.agents.output_parser import AgentOutputParseError, AgentOutputParser


def test_parser_accepts_valid_actions() -> None:
    parser = AgentOutputParser()

    buy = parser.parse(
        '{"action": "BUY", "tradeIntent": "OPEN_LONG", '
        '"targetExposurePct": 0.25, "confidence": 0.75, '
        '"primaryDriver": "TECHNICAL", "newInformation": true, '
        '"rationale": "Buy rationale."}'
    )
    hold = parser.parse(
        '{"action": "HOLD", "tradeIntent": "STAY_OUT", '
        '"targetExposurePct": 0, "confidence": 0, '
        '"primaryDriver": "PORTFOLIO", "newInformation": false, '
        '"rationale": "Hold rationale."}'
    )
    sell = parser.parse(
        '{"action": "SELL", "tradeIntent": "CLOSE_LONG", '
        '"targetExposurePct": 0, "confidence": 1, '
        '"primaryDriver": "RISK", "newInformation": true, '
        '"rationale": "Sell rationale."}'
    )

    assert buy.action is TradeAction.BUY
    assert buy.trade_intent is TradeIntent.OPEN_LONG
    assert buy.target_exposure_pct == Decimal("0.2500")
    assert buy.confidence == Decimal("0.7500")
    assert buy.primary_driver is PrimaryDriver.TECHNICAL
    assert buy.new_information is True
    assert hold.action is TradeAction.HOLD
    assert sell.action is TradeAction.SELL


@pytest.mark.parametrize(
    "raw_output",
    [
        "not json",
        "[]",
        '{"action": "WAIT", "tradeIntent": "OPEN_LONG", "targetExposurePct": 0.5, '
        '"confidence": 0.5, "primaryDriver": "TECHNICAL", '
        '"newInformation": true, "rationale": "bad action"}',
        '{"action": "BUY", "tradeIntent": "OPEN_LONG", "targetExposurePct": 1.2, '
        '"confidence": 0.5, "primaryDriver": "TECHNICAL", '
        '"newInformation": true, "rationale": "bad exposure"}',
        '{"action": "BUY", "tradeIntent": "OPEN_LONG", "targetExposurePct": 0.5, '
        '"confidence": 2, "primaryDriver": "TECHNICAL", '
        '"newInformation": true, "rationale": "bad confidence"}',
        '{"action": "BUY", "tradeIntent": "OPEN_LONG", "targetExposurePct": 0.5, '
        '"confidence": 0.5, "primaryDriver": "TECHNICAL", '
        '"newInformation": true, "rationale": ""}',
    ],
)
def test_parser_rejects_invalid_output(raw_output: str) -> None:
    with pytest.raises(AgentOutputParseError):
        AgentOutputParser().parse(raw_output)
