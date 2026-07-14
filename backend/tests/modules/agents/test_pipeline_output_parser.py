import pytest

from app.domain.enums import TradeAction
from app.modules.agents.output_parser import AgentOutputParseError
from app.modules.agents.pipeline_output_parser import PipelineOutputParser
from app.modules.agents.pipeline_types import MarketBias, RiskLevel


def test_pipeline_parser_accepts_multi_agent_stage_outputs() -> None:
    parser = PipelineOutputParser()

    fundamental = parser.parse_fundamental_analysis(
        '{"signal": "BULLISH", "confidence": 0.8, "summary": "Healthy business."}'
    )
    sentiment = parser.parse_sentiment_analysis(
        '{"signal": "NEUTRAL", "confidence": 0.4, "summary": "Mixed headlines."}'
    )
    risk = parser.parse_risk_assessment(
        '{"riskLevel": "MEDIUM", "confidence": 0.9, "summary": "Manageable risk."}'
    )
    decision = parser.parse_portfolio_decision(
        '{"action": "BUY", "tradeIntent": "OPEN_LONG", '
        '"targetExposurePct": 0.35, "confidence": 0.7, '
        '"primaryDriver": "TECHNICAL", "newInformation": true, '
        '"rationale": "Net positive setup."}'
    )

    assert fundamental.signal is MarketBias.BULLISH
    assert sentiment.signal is MarketBias.NEUTRAL
    assert risk.risk_level is RiskLevel.MEDIUM
    assert decision.action is TradeAction.BUY


def test_pipeline_parser_accepts_json_inside_markdown_fence() -> None:
    parser = PipelineOutputParser()

    output = parser.parse_fundamental_analysis(
        '```json\n{"signal": "NEUTRAL", "confidence": 0.5, '
        '"summary": "No structured inputs."}\n```'
    )

    assert output.signal is MarketBias.NEUTRAL


def test_pipeline_parser_accepts_json_with_surrounding_text() -> None:
    parser = PipelineOutputParser()

    output = parser.parse_risk_assessment(
        'Here is the assessment:\n{"riskLevel": "LOW", "confidence": 0.6, '
        '"summary": "Risk is controlled."}\nDone.'
    )

    assert output.risk_level is RiskLevel.LOW


@pytest.mark.parametrize(
    "parse_method,raw_output",
    [
        ("parse_fundamental_analysis", "not json"),
        ("parse_fundamental_analysis", '{"signal": "BULLISH", '),
        ("parse_fundamental_analysis", '{"confidence": 0.8, "summary": "Missing."}'),
        (
            "parse_fundamental_analysis",
            '{"signal": "SIDEWAYS", "confidence": 0.8, "summary": "Bad."}',
        ),
        (
            "parse_sentiment_analysis",
            '{"signal": "BULLISH", "confidence": 2, "summary": "Bad."}',
        ),
        (
            "parse_risk_assessment",
            '{"riskLevel": "EXTREME", "confidence": 0.8, "summary": "Bad."}',
        ),
        (
            "parse_portfolio_decision",
            '{"action": "WAIT", "tradeIntent": "OPEN_LONG", '
            '"targetExposurePct": 0.4, "confidence": 0.8, '
            '"primaryDriver": "TECHNICAL", "newInformation": true, '
            '"rationale": "Bad."}',
        ),
        (
            "parse_portfolio_decision",
            '{"action": "HOLD", "tradeIntent": "STAY_OUT", '
            '"targetExposurePct": 0, "confidence": 0.8, '
            '"primaryDriver": "PORTFOLIO", "newInformation": false, '
            '"rationale": ""}',
        ),
    ],
)
def test_pipeline_parser_rejects_invalid_multi_agent_outputs(
    parse_method: str, raw_output: str
) -> None:
    parser = PipelineOutputParser()
    with pytest.raises(AgentOutputParseError):
        getattr(parser, parse_method)(raw_output)
