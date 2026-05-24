import json
from typing import Any

from app.modules.agents.pipeline_types import (
    MarketAnalysisOutput,
    PipelineProvider,
)
from app.modules.agents.types import (
    AgentContext,
    AgentProviderResponse,
    ParsedAgentOutput,
)


class FakePipelineProvider(PipelineProvider):
    provider_name = "deterministic-fake-pipeline"
    model_version = "v1"

    def complete_market_analyst(
        self, prompt: str, context: AgentContext
    ) -> AgentProviderResponse:
        _ = prompt
        return self._response(
            context,
            self._value(
                context.parameters_json,
                "marketAnalystOutput",
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
        return self._optional_response(context, "marketAnalystRepairOutput")

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
                "tradingDecisionOutput",
                {
                    "action": "HOLD",
                    "confidence": 0,
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
        return self._optional_response(context, "tradingDecisionRepairOutput")

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
                "riskManagerOutput",
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
        return self._optional_response(context, "riskManagerRepairOutput")

    def _optional_response(
        self, context: AgentContext, key: str
    ) -> AgentProviderResponse | None:
        parameters = self._pipeline_parameters(context.parameters_json)
        if key not in parameters:
            return None
        return self._response(context, parameters[key])

    def _response(self, context: AgentContext, value: Any) -> AgentProviderResponse:
        return AgentProviderResponse(
            raw_output_text=self._to_text(value),
            model_name=context.model_name or self.provider_name,
            model_version=self.model_version,
        )

    def _value(
        self, parameters_json: dict[str, Any] | None, key: str, default: Any
    ) -> Any:
        return self._pipeline_parameters(parameters_json).get(key, default)

    def _pipeline_parameters(
        self, parameters_json: dict[str, Any] | None
    ) -> dict[str, Any]:
        parameters = parameters_json or {}
        fake_pipeline = parameters.get("fakePipeline")
        if isinstance(fake_pipeline, dict):
            return fake_pipeline
        return {}

    def _to_text(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value, sort_keys=True)
