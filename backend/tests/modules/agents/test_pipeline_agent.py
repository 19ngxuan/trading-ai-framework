from datetime import date, datetime
from decimal import Decimal

from app.domain.enums import AgentMode, AgentStepName, ParsingStatus, TradeAction
from app.modules.agents.fake_pipeline_provider import FakePipelineProvider
from app.modules.agents.pipeline_agent import AgentDecisionPipeline
from app.modules.agents.types import AgentContext
from app.modules.market_data.intraday_provider import IntradayBar
from app.modules.market_data.provider import DailyBar


class FundamentalRaisesProvider(FakePipelineProvider):
    def complete_fundamental_analyst(self, prompt: str, context: AgentContext, research):
        raise RuntimeError("fundamental failed")


class PortfolioRepairRaisesProvider(FakePipelineProvider):
    def repair_portfolio_manager(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ):
        raise RuntimeError("portfolio repair failed")


class PortfolioRepairSequenceProvider(FakePipelineProvider):
    def __init__(self, repair_outputs: list[str]) -> None:
        self.repair_outputs = repair_outputs
        self.repair_calls = 0

    def repair_portfolio_manager(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ):
        _ = (prompt, raw_output_text, error_message)
        output = self.repair_outputs[self.repair_calls]
        self.repair_calls += 1
        return self._response(context, output)


class TrackingTechnicalProvider(FakePipelineProvider):
    def __init__(self) -> None:
        self.technical_calls = 0

    def complete_technical_analyst(self, prompt, context, technical_snapshot):
        self.technical_calls += 1
        return super().complete_technical_analyst(prompt, context, technical_snapshot)


class FakeRangeProvider:
    def load_range(self, start_date, end_date, symbol="SPY", frequency=None):
        _ = (start_date, end_date, frequency)
        base = Decimal("100") if symbol == "SPY" else Decimal("200")
        return [
            DailyBar(
                date=date(2024, 1, day),
                open=base + Decimal(day),
                high=base + Decimal(day) + Decimal("1"),
                low=base + Decimal(day) - Decimal("1"),
                close=base + Decimal(day),
                adjusted_close=base + Decimal(day),
                volume=Decimal("1000000") + Decimal(day),
                raw={"symbol": symbol},
            )
            for day in range(1, 29)
        ]

    def get_latest_bar(self, symbol="SPY"):
        return self.load_range(date(2024, 1, 1), date(2024, 1, 28), symbol)[-1]


class FakeIntradayProvider:
    def load_range(self, start_date, end_date, symbol="SPY", frequency=None):
        _ = (start_date, end_date, symbol, frequency)
        return []

    def load_session_until(self, session_date, through_timestamp, symbol="SPY", frequency=None):
        _ = (through_timestamp, symbol, frequency)
        return [
            IntradayBar(
                timestamp=datetime(2024, 1, 2, 10, 0),
                session_date=session_date,
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("101"),
                volume=Decimal("10000"),
                raw={},
            )
        ]


def _context(
    parameters_json: dict | None,
    confidence_threshold: Decimal | None = None,
) -> AgentContext:
    return AgentContext(
        experiment_id=1,
        execution_step_id=1,
        symbol="SPY",
        bar=DailyBar(
            date=date(2024, 1, 2),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            adjusted_close=Decimal("100"),
            volume=Decimal("1000000"),
            raw={"date": "2024-01-02"},
            timestamp=datetime(2024, 1, 2, 10, 0),
        ),
        cash=Decimal("10000"),
        position_quantity=Decimal("0"),
        current_portfolio_value=Decimal("10000"),
        confidence_threshold=confidence_threshold,
        parameters_json=parameters_json,
        agent_mode=AgentMode.PIPELINE,
        model_name=None,
    )


def _multi_agent_outputs(
    action: str = "BUY",
    confidence: float = 0.8,
) -> dict:
    return {
        "fakeMultiAgent": {
            "fundamentalAnalystOutput": {
                "signal": "BULLISH",
                "confidence": 0.8,
                "summary": "Healthy fundamentals.",
            },
            "sentimentAnalystOutput": {
                "signal": "BULLISH",
                "confidence": 0.7,
                "summary": "Constructive sentiment.",
            },
            "riskAssessmentOutput": {
                "riskLevel": "MEDIUM",
                "confidence": 0.9,
                "summary": "Risk remains manageable.",
            },
            "portfolioManagerOutput": {
                "action": action,
                "confidence": confidence,
                "rationale": "Multi-agent portfolio manager is constructive.",
            },
        }
    }


def _fenced_json(value: str) -> str:
    return f"```json\n{value}\n```"


def test_multi_agent_buy_returns_six_logs() -> None:
    result = AgentDecisionPipeline().run(_context(_multi_agent_outputs()))

    assert result.decision.action is TradeAction.BUY
    assert len(result.log_payloads) == 6
    assert [payload.agent_step_name for payload in result.log_payloads] == [
        AgentStepName.FETCH_DATA,
        AgentStepName.TECHNICAL_ANALYST,
        AgentStepName.FUNDAMENTAL_ANALYST,
        AgentStepName.SENTIMENT_ANALYST,
        AgentStepName.RISK_MANAGER,
        AgentStepName.PORTFOLIO_MANAGER,
    ]
    assert result.log_payloads[0].parsing_status is ParsingStatus.SUCCESS


def test_multi_agent_fetches_research_context_and_calls_technical_agent() -> None:
    provider = TrackingTechnicalProvider()
    result = AgentDecisionPipeline(
        provider=provider,
        market_data_provider=FakeRangeProvider(),
        intraday_provider=FakeIntradayProvider(),
    ).run(
        _context(
            {
                **_multi_agent_outputs(),
                "fundamentalData": {"peRatio": 20, "notes": "Profitable."},
                "sentimentData": {
                    "headlines": ["Constructive product news"],
                    "transcriptSummaries": [{"quarter": 1}],
                },
            }
        )
    )

    fetch_payload = result.log_payloads[0].parsed_output_json
    technical_payload = result.log_payloads[1].parsed_output_json

    assert provider.technical_calls == 1
    assert fetch_payload["fundamentalDataAvailable"] is True
    assert fetch_payload["newsDataAvailable"] is True
    assert fetch_payload["transcriptDataAvailable"] is True
    assert fetch_payload["intradayDataAvailable"] is True
    assert fetch_payload["benchmarkDataAvailable"] is True
    assert technical_payload["indicators"]["macd"]["histogram"] is not None


def test_multi_agent_accepts_fenced_json_for_llm_stages() -> None:
    result = AgentDecisionPipeline().run(
        _context(
            {
                "fakeMultiAgent": {
                    "fundamentalAnalystOutput": _fenced_json(
                        '{"signal":"BULLISH","confidence":0.8,'
                        '"summary":"Healthy fundamentals."}'
                    ),
                    "sentimentAnalystOutput": _fenced_json(
                        '{"signal":"BULLISH","confidence":0.7,'
                        '"summary":"Constructive sentiment."}'
                    ),
                    "riskAssessmentOutput": _fenced_json(
                        '{"riskLevel":"LOW","confidence":0.9,'
                        '"summary":"Risk remains low."}'
                    ),
                    "portfolioManagerOutput": _fenced_json(
                        '{"action":"BUY","tradeIntent":"OPEN_LONG",'
                        '"targetExposurePct":0.25,"confidence":0.8,'
                        '"primaryDriver":"TECHNICAL","newInformation":true,'
                        '"rationale":"Multi-agent portfolio manager is constructive.",'
                        '"eventId":null}'
                    ),
                }
            }
        )
    )

    assert result.decision.action is TradeAction.BUY
    assert [
        payload.parsing_status for payload in result.log_payloads[2:]
    ] == [ParsingStatus.SUCCESS] * 4


def test_multi_agent_low_confidence_returns_hold() -> None:
    result = AgentDecisionPipeline().run(
        _context(_multi_agent_outputs(confidence=0.2), Decimal("0.7000"))
    )

    assert result.decision.action is TradeAction.HOLD
    assert result.decision.raw_decision_json["fallbackReason"] == (
        "CONFIDENCE_BELOW_THRESHOLD"
    )
    assert result.decision.raw_decision_json["originalAction"] == "BUY"
    assert result.decision.raw_decision_json["finalAction"] == "HOLD"


def test_multi_agent_defaults_to_hold_when_no_fake_outputs_exist() -> None:
    result = AgentDecisionPipeline().run(_context(None))

    assert result.decision.action is TradeAction.HOLD
    assert len(result.log_payloads) == 6


def test_multi_agent_stage_provider_exception_uses_fallback_stage() -> None:
    result = AgentDecisionPipeline(provider=FundamentalRaisesProvider()).run(
        _context(_multi_agent_outputs())
    )

    assert result.decision.action is TradeAction.BUY
    assert result.log_payloads[2].parsing_status is ParsingStatus.FAILED
    assert result.log_payloads[2].parsed_output_json["fallbackReason"] == (
        "PROVIDER_COMPLETE_EXCEPTION"
    )
    assert result.decision.raw_decision_json["degradedStages"] == [
        AgentStepName.FUNDAMENTAL_ANALYST.value
    ]


def test_multi_agent_portfolio_repair_exception_falls_back_to_hold() -> None:
    result = AgentDecisionPipeline(provider=PortfolioRepairRaisesProvider()).run(
        _context(
            {
                "fakeMultiAgent": {
                    "fundamentalAnalystOutput": {
                        "signal": "BULLISH",
                        "confidence": 0.8,
                        "summary": "Healthy fundamentals.",
                    },
                    "sentimentAnalystOutput": {
                        "signal": "BULLISH",
                        "confidence": 0.7,
                        "summary": "Constructive sentiment.",
                    },
                    "riskAssessmentOutput": {
                        "riskLevel": "LOW",
                        "confidence": 0.9,
                        "summary": "Low operational risk.",
                    },
                    "portfolioManagerOutput": "not json",
                }
            }
        )
    )

    assert result.decision.action is TradeAction.HOLD
    assert result.log_payloads[-1].parsing_status is ParsingStatus.FAILED
    assert result.decision.raw_decision_json["fallbackReason"] == (
        "PORTFOLIO_MANAGER_STAGE_FAILED"
    )


def test_multi_agent_repair_succeeds_with_fenced_json_on_second_attempt() -> None:
    provider = PortfolioRepairSequenceProvider(
        [
            "still not json",
            _fenced_json(
                '{"action":"BUY","tradeIntent":"OPEN_LONG",'
                '"targetExposurePct":0.25,"confidence":0.8,'
                '"primaryDriver":"TECHNICAL","newInformation":true,'
                '"rationale":"Repaired portfolio decision.","eventId":null}'
            ),
        ]
    )

    result = AgentDecisionPipeline(provider=provider).run(
        _context(
            {
                "fakeMultiAgent": {
                    "fundamentalAnalystOutput": {
                        "signal": "BULLISH",
                        "confidence": 0.8,
                        "summary": "Healthy fundamentals.",
                    },
                    "sentimentAnalystOutput": {
                        "signal": "BULLISH",
                        "confidence": 0.7,
                        "summary": "Constructive sentiment.",
                    },
                    "riskAssessmentOutput": {
                        "riskLevel": "LOW",
                        "confidence": 0.9,
                        "summary": "Low operational risk.",
                    },
                    "portfolioManagerOutput": "not json",
                }
            }
        )
    )

    assert result.decision.action is TradeAction.BUY
    assert provider.repair_calls == 2
    assert result.log_payloads[-1].parsing_status is ParsingStatus.REPAIRED


def test_multi_agent_falls_back_after_two_invalid_repair_attempts() -> None:
    provider = PortfolioRepairSequenceProvider(["still not json", "also not json"])

    result = AgentDecisionPipeline(provider=provider).run(
        _context(
            {
                "fakeMultiAgent": {
                    "fundamentalAnalystOutput": {
                        "signal": "BULLISH",
                        "confidence": 0.8,
                        "summary": "Healthy fundamentals.",
                    },
                    "sentimentAnalystOutput": {
                        "signal": "BULLISH",
                        "confidence": 0.7,
                        "summary": "Constructive sentiment.",
                    },
                    "riskAssessmentOutput": {
                        "riskLevel": "LOW",
                        "confidence": 0.9,
                        "summary": "Low operational risk.",
                    },
                    "portfolioManagerOutput": "not json",
                }
            }
        )
    )

    assert result.decision.action is TradeAction.HOLD
    assert provider.repair_calls == 2
    assert result.log_payloads[-1].parsing_status is ParsingStatus.FAILED
    assert result.log_payloads[-1].parsed_output_json["fallbackReason"] == (
        "REPAIR_PARSE_FAILED"
    )
