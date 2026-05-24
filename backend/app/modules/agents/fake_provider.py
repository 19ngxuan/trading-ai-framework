import json
from typing import Any

from app.modules.agents.types import (
    AgentContext,
    AgentProviderResponse,
)


class FakeAgentProvider:
    provider_name = "deterministic-fake-agent"
    model_version = "v1"

    def complete(self, prompt: str, context: AgentContext) -> AgentProviderResponse:
        _ = prompt
        raw_output = self._configured_value(
            context.parameters_json,
            keys=("output", "agentOutput"),
            default={
                "action": "HOLD",
                "confidence": 0,
                "rationale": "Deterministic fake agent defaulted to HOLD.",
            },
        )
        return AgentProviderResponse(
            raw_output_text=self._to_text(raw_output),
            model_name=context.model_name or self.provider_name,
            model_version=self.model_version,
        )

    def repair(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        _ = (prompt, raw_output_text, error_message)
        raw_output = self._configured_value(
            context.parameters_json,
            keys=("repairOutput", "agentRepairOutput"),
            default=None,
        )
        if raw_output is None:
            return None
        return AgentProviderResponse(
            raw_output_text=self._to_text(raw_output),
            model_name=context.model_name or self.provider_name,
            model_version=self.model_version,
        )

    def _configured_value(
        self,
        parameters_json: dict[str, Any] | None,
        *,
        keys: tuple[str, ...],
        default: Any,
    ) -> Any:
        parameters = parameters_json or {}
        fake_config = parameters.get("fakeAgent")
        if isinstance(fake_config, dict):
            for key in keys:
                if key in fake_config:
                    return fake_config[key]

        for key in keys:
            if key in parameters:
                return parameters[key]

        if all(key in parameters for key in ("agentAction", "agentConfidence", "agentRationale")):
            return {
                "action": parameters["agentAction"],
                "confidence": parameters["agentConfidence"],
                "rationale": parameters["agentRationale"],
            }
        return default

    def _to_text(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value, sort_keys=True)
