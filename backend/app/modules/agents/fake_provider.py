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
                "tradeIntent": "STAY_OUT",
                "targetExposurePct": 0,
                "confidence": 0,
                "primaryDriver": "PORTFOLIO",
                "newInformation": False,
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
                "tradeIntent": parameters.get("agentTradeIntent", "STAY_OUT"),
                "targetExposurePct": parameters.get("agentTargetExposurePct", 0),
                "confidence": parameters["agentConfidence"],
                "primaryDriver": parameters.get("agentPrimaryDriver", "PORTFOLIO"),
                "newInformation": parameters.get("agentNewInformation", False),
                "rationale": parameters["agentRationale"],
            }
        return default

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
