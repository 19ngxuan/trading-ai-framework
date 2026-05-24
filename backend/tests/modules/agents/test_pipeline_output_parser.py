from decimal import Decimal

import pytest

from app.domain.enums import TradeAction
from app.modules.agents.output_parser import AgentOutputParseError
from app.modules.agents.pipeline_output_parser import PipelineOutputParser
from app.modules.agents.pipeline_types import MarketBias, RiskManagerVerdict


def test_pipeline_parser_accepts_valid_stage_outputs() -> None:
    parser = PipelineOutputParser()

    market = parser.parse_market_analysis(
        '{"marketBias": "BULLISH", "confidence": 0.8, "rationale": "Bullish."}'
    )
    decision = parser.parse_trading_decision(
        '{"action": "BUY", "confidence": 0.7, "rationale": "Buy."}'
    )
    risk = parser.parse_risk_manager(
        '{"verdict": "APPROVE", "confidence": 0.9, "rationale": "Approved."}'
    )

    assert market.market_bias is MarketBias.BULLISH
    assert market.confidence == Decimal("0.8000")
    assert decision.action is TradeAction.BUY
    assert decision.confidence == Decimal("0.7000")
    assert risk.verdict is RiskManagerVerdict.APPROVE
    assert risk.confidence == Decimal("0.9000")


@pytest.mark.parametrize(
    "parse_method,raw_output",
    [
        ("parse_market_analysis", "not json"),
        (
            "parse_market_analysis",
            '{"marketBias": "SIDEWAYS", "confidence": 0.8, "rationale": "Bad."}',
        ),
        (
            "parse_trading_decision",
            '{"action": "WAIT", "confidence": 0.8, "rationale": "Bad."}',
        ),
        (
            "parse_risk_manager",
            '{"verdict": "MAYBE", "confidence": 0.8, "rationale": "Bad."}',
        ),
        (
            "parse_risk_manager",
            '{"verdict": "APPROVE", "confidence": 2, "rationale": "Bad."}',
        ),
        (
            "parse_trading_decision",
            '{"action": "HOLD", "confidence": 0.8, "rationale": ""}',
        ),
    ],
)
def test_pipeline_parser_rejects_invalid_stage_outputs(
    parse_method: str, raw_output: str
) -> None:
    parser = PipelineOutputParser()
    with pytest.raises(AgentOutputParseError):
        getattr(parser, parse_method)(raw_output)
