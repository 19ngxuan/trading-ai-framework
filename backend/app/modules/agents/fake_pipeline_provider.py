import json
from typing import Any

from app.modules.agents.pipeline_types import (
    FundamentalResearchSnapshot,
    MarketAnalysisOutput,
    PipelineProvider,
    RiskAssessmentOutput,
    SentimentResearchSnapshot,
    TechnicalAnalysisOutput,
)
from app.modules.agents.types import AgentContext, AgentProviderResponse, ParsedAgentOutput


class FakePipelineProvider(PipelineProvider):
    provider_name = "deterministic-fake-multi-agent"
    model_version = "v1"

    def complete_technical_analyst(
        self,
        prompt: str,
        context: AgentContext,
        technical_snapshot: TechnicalAnalysisOutput,
    ) -> AgentProviderResponse:
        _ = (prompt, technical_snapshot)
        return self._response(
            context,
            self._value(
                context.parameters_json,
                ("technicalAnalystOutput",),
                {
                    "signal": technical_snapshot.signal.value,
                    "confidence": float(technical_snapshot.confidence),
                    "summary": technical_snapshot.rationale,
                    "rsi": float(technical_snapshot.rsi)
                    if technical_snapshot.rsi is not None
                    else None,
                    "sma20": float(technical_snapshot.sma_20)
                    if technical_snapshot.sma_20 is not None
                    else None,
                    "trend": technical_snapshot.trend,
                    "volatilityPct": float(technical_snapshot.volatility_pct)
                    if technical_snapshot.volatility_pct is not None
                    else None,
                    "indicators": technical_snapshot.indicators or {},
                    "timeHorizonSignals": technical_snapshot.time_horizon_signals or {},
                    "riskNotes": technical_snapshot.risk_notes or [],
                },
            ),
        )

    def repair_technical_analyst(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        _ = (prompt, raw_output_text, error_message)
        return self._optional_response(context, ("technicalAnalystRepairOutput",))

    def complete_market_analyst(
        self, prompt: str, context: AgentContext
    ) -> AgentProviderResponse:
        _ = prompt
        return self._response(
            context,
            self._value(
                context.parameters_json,
                ("marketAnalystOutput",),
                {
                    "marketBias": "NEUTRAL",
                    "confidence": 0,
                    "rationale": "Deterministic fake pipeline defaulted to neutral analysis.",
                },
            ),
        )

    def repair_market_analyst(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        _ = (prompt, raw_output_text, error_message)
        return self._optional_response(context, ("marketAnalystRepairOutput",))

    def complete_trading_decision(
        self,
        prompt: str,
        context: AgentContext,
        market_analysis: MarketAnalysisOutput,
    ) -> AgentProviderResponse:
        _ = (prompt, market_analysis)
        return self._response(
            context,
            self._value(
                context.parameters_json,
                ("tradingDecisionOutput", "portfolioManagerOutput"),
                {
                    "action": "HOLD",
                    "tradeIntent": "STAY_OUT",
                    "targetExposurePct": 0,
                    "confidence": 0,
                    "primaryDriver": "PORTFOLIO",
                    "newInformation": False,
                    "rationale": "Deterministic fake pipeline defaulted to HOLD.",
                },
            ),
        )

    def repair_trading_decision(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        _ = (prompt, raw_output_text, error_message)
        return self._optional_response(
            context,
            ("tradingDecisionRepairOutput", "portfolioManagerRepairOutput"),
        )

    def complete_risk_manager(
        self,
        prompt: str,
        context: AgentContext,
        market_analysis: MarketAnalysisOutput,
        proposed_decision: ParsedAgentOutput,
    ) -> AgentProviderResponse:
        _ = (prompt, market_analysis, proposed_decision)
        return self._response(
            context,
            self._value(
                context.parameters_json,
                ("riskManagerOutput",),
                {
                    "verdict": "APPROVE",
                    "confidence": 0,
                    "rationale": "Deterministic fake pipeline approved the default HOLD.",
                },
            ),
        )

    def repair_risk_manager(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        _ = (prompt, raw_output_text, error_message)
        return self._optional_response(context, ("riskManagerRepairOutput",))

    def complete_fundamental_analyst(
        self,
        prompt: str,
        context: AgentContext,
        research_snapshot: FundamentalResearchSnapshot,
    ) -> AgentProviderResponse:
        _ = (prompt, research_snapshot)
        return self._response(
            context,
            self._value(
                context.parameters_json,
                ("fundamentalAnalystOutput",),
                {
                    "signal": "NEUTRAL",
                    "confidence": 0,
                    "summary": "Deterministic fake multi-agent defaulted to neutral fundamentals.",
                },
            ),
        )

    def repair_fundamental_analyst(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        _ = (prompt, raw_output_text, error_message)
        return self._optional_response(context, ("fundamentalAnalystRepairOutput",))

    def complete_sentiment_analyst(
        self,
        prompt: str,
        context: AgentContext,
        research_snapshot: SentimentResearchSnapshot,
        technical_analysis: TechnicalAnalysisOutput,
    ) -> AgentProviderResponse:
        _ = (prompt, research_snapshot, technical_analysis)
        return self._response(
            context,
            self._value(
                context.parameters_json,
                ("sentimentAnalystOutput",),
                {
                    "signal": "NEUTRAL",
                    "confidence": 0,
                    "summary": "Deterministic fake multi-agent defaulted to neutral sentiment.",
                },
            ),
        )

    def repair_sentiment_analyst(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        _ = (prompt, raw_output_text, error_message)
        return self._optional_response(context, ("sentimentAnalystRepairOutput",))

    def complete_risk_assessment(
        self,
        prompt: str,
        context: AgentContext,
        technical_analysis: TechnicalAnalysisOutput,
        fundamental_analysis,
        sentiment_analysis,
    ) -> AgentProviderResponse:
        _ = (prompt, technical_analysis, fundamental_analysis, sentiment_analysis)
        return self._response(
            context,
            self._value(
                context.parameters_json,
                ("riskAssessmentOutput",),
                {
                    "riskLevel": "MEDIUM",
                    "confidence": 0,
                    "summary": "Deterministic fake multi-agent defaulted to medium risk.",
                },
            ),
        )

    def repair_risk_assessment(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        _ = (prompt, raw_output_text, error_message)
        return self._optional_response(context, ("riskAssessmentRepairOutput",))

    def complete_portfolio_manager(
        self,
        prompt: str,
        context: AgentContext,
        technical_analysis: TechnicalAnalysisOutput,
        fundamental_analysis,
        sentiment_analysis,
        risk_assessment: RiskAssessmentOutput,
    ) -> AgentProviderResponse:
        _ = (
            prompt,
            technical_analysis,
            fundamental_analysis,
            sentiment_analysis,
            risk_assessment,
        )
        return self._response(
            context,
            self._value(
                context.parameters_json,
                ("portfolioManagerOutput", "tradingDecisionOutput"),
                {
                    "action": "HOLD",
                    "tradeIntent": "STAY_OUT",
                    "targetExposurePct": 0,
                    "confidence": 0,
                    "primaryDriver": "PORTFOLIO",
                    "newInformation": False,
                    "rationale": "Deterministic fake multi-agent defaulted to HOLD.",
                },
            ),
        )

    def repair_portfolio_manager(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        _ = (prompt, raw_output_text, error_message)
        return self._optional_response(
            context,
            ("portfolioManagerRepairOutput", "tradingDecisionRepairOutput"),
        )

    def _optional_response(
        self, context: AgentContext, keys: tuple[str, ...]
    ) -> AgentProviderResponse | None:
        parameters = self._pipeline_parameters(context.parameters_json)
        for key in keys:
            if key in parameters:
                return self._response(context, parameters[key])
        return None

    def _response(self, context: AgentContext, value: Any) -> AgentProviderResponse:
        return AgentProviderResponse(
            raw_output_text=self._to_text(value),
            model_name=context.model_name or self.provider_name,
            model_version=self.model_version,
        )

    def _value(
        self,
        parameters_json: dict[str, Any] | None,
        keys: tuple[str, ...],
        default: Any,
    ) -> Any:
        parameters = self._pipeline_parameters(parameters_json)
        for key in keys:
            if key in parameters:
                return parameters[key]
        return default

    def _pipeline_parameters(
        self, parameters_json: dict[str, Any] | None
    ) -> dict[str, Any]:
        parameters = parameters_json or {}
        for key in ("fakeMultiAgent", "fakePipeline"):
            payload = parameters.get(key)
            if isinstance(payload, dict):
                return payload
        return {}

    def _to_text(self, value: Any) -> str:
        if isinstance(value, dict) and "action" in value:
            value = self._with_v2_defaults(value)
        if isinstance(value, str):
            return value
        return json.dumps(value, sort_keys=True)

    def _with_v2_defaults(self, value: dict[str, Any]) -> dict[str, Any]:
        action = str(value.get("action", "HOLD")).upper()
        default_intent = {
            "BUY": "OPEN_LONG",
            "SELL": "CLOSE_LONG",
            "HOLD": "STAY_OUT",
        }.get(action, "STAY_OUT")
        return {
            "tradeIntent": default_intent,
            "targetExposurePct": 0.25 if action == "BUY" else 0,
            "primaryDriver": "TECHNICAL" if action in {"BUY", "SELL"} else "PORTFOLIO",
            "newInformation": action == "BUY",
            **value,
        }
