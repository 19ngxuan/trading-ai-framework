from typing import Any

import httpx

from app.modules.agents.errors import AgentProviderError
from app.modules.agents.types import (
    AgentContext,
    AgentProviderResponse,
)
from app.modules.agents.pipeline_types import (
    FundamentalResearchSnapshot,
    MarketAnalysisOutput,
    RiskAssessmentOutput,
    SentimentResearchSnapshot,
    TechnicalAnalysisOutput,
)
from app.modules.agents.types import ParsedAgentOutput


class ScadsAIAgentProvider:
    provider_name = "scads-ai"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://llm.scads.ai/v1",
        timeout_seconds: int = 30,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.client = client or httpx.Client(timeout=timeout_seconds)

    def complete(self, prompt: str, context: AgentContext) -> AgentProviderResponse:
        return self._chat_completion(prompt=prompt, context=context)

    def repair(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        _ = (raw_output_text, error_message)
        return self._chat_completion(prompt=prompt, context=context)

    def _chat_completion(
        self,
        *,
        prompt: str,
        context: AgentContext,
    ) -> AgentProviderResponse:
        model = context.model_name
        if not model:
            raise AgentProviderError("ScaDS.AI model name is required.")
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an advisory trading decision model. Return strict "
                        "JSON only. You have no tools and cannot execute trades."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        }
        try:
            response = self.client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise AgentProviderError(
                "ScaDS.AI request failed.",
                details={
                    "statusCode": exc.response.status_code,
                    "responseText": exc.response.text,
                },
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise AgentProviderError(
                "ScaDS.AI request failed.",
                details={"error": str(exc)},
            ) from exc

        return AgentProviderResponse(
            raw_output_text=self._extract_content(data),
            model_name=str(data.get("model") or model),
            model_version=None,
        )

    def _extract_content(self, payload: Any) -> str:
        if not isinstance(payload, dict):
            raise AgentProviderError(
                "ScaDS.AI response is malformed.",
                details={"payload": payload},
            )
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise AgentProviderError(
                "ScaDS.AI response did not include choices.",
                details={"payload": payload},
            )
        first = choices[0]
        if not isinstance(first, dict):
            raise AgentProviderError(
                "ScaDS.AI response choice is malformed.",
                details={"payload": payload},
            )
        message = first.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise AgentProviderError(
                "ScaDS.AI response message is malformed.",
                details={"payload": payload},
            )
        return message["content"]


class ScadsAIPipelineProvider(ScadsAIAgentProvider):
    provider_name = "scads-ai-pipeline"

    def complete_market_analyst(
        self, prompt: str, context: AgentContext
    ) -> AgentProviderResponse:
        return self._chat_completion(prompt=prompt, context=context)

    def repair_market_analyst(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        _ = (raw_output_text, error_message)
        return self._chat_completion(prompt=prompt, context=context)

    def complete_trading_decision(
        self,
        prompt: str,
        context: AgentContext,
        market_analysis: MarketAnalysisOutput,
    ) -> AgentProviderResponse:
        _ = market_analysis
        return self._chat_completion(prompt=prompt, context=context)

    def repair_trading_decision(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        _ = (raw_output_text, error_message)
        return self._chat_completion(prompt=prompt, context=context)

    def complete_risk_manager(
        self,
        prompt: str,
        context: AgentContext,
        market_analysis: MarketAnalysisOutput,
        proposed_decision: ParsedAgentOutput,
    ) -> AgentProviderResponse:
        _ = (market_analysis, proposed_decision)
        return self._chat_completion(prompt=prompt, context=context)

    def repair_risk_manager(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        _ = (raw_output_text, error_message)
        return self._chat_completion(prompt=prompt, context=context)

    def complete_fundamental_analyst(
        self,
        prompt: str,
        context: AgentContext,
        research_snapshot: FundamentalResearchSnapshot,
    ) -> AgentProviderResponse:
        _ = research_snapshot
        return self._chat_completion(prompt=prompt, context=context)

    def repair_fundamental_analyst(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        _ = (raw_output_text, error_message)
        return self._chat_completion(prompt=prompt, context=context)

    def complete_sentiment_analyst(
        self,
        prompt: str,
        context: AgentContext,
        research_snapshot: SentimentResearchSnapshot,
        technical_analysis: TechnicalAnalysisOutput,
    ) -> AgentProviderResponse:
        _ = (research_snapshot, technical_analysis)
        return self._chat_completion(prompt=prompt, context=context)

    def repair_sentiment_analyst(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        _ = (raw_output_text, error_message)
        return self._chat_completion(prompt=prompt, context=context)

    def complete_risk_assessment(
        self,
        prompt: str,
        context: AgentContext,
        technical_analysis: TechnicalAnalysisOutput,
        fundamental_analysis: object,
        sentiment_analysis: object,
    ) -> AgentProviderResponse:
        _ = (technical_analysis, fundamental_analysis, sentiment_analysis)
        return self._chat_completion(prompt=prompt, context=context)

    def repair_risk_assessment(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        _ = (raw_output_text, error_message)
        return self._chat_completion(prompt=prompt, context=context)

    def complete_portfolio_manager(
        self,
        prompt: str,
        context: AgentContext,
        technical_analysis: TechnicalAnalysisOutput,
        fundamental_analysis: object,
        sentiment_analysis: object,
        risk_assessment: RiskAssessmentOutput,
    ) -> AgentProviderResponse:
        _ = (
            technical_analysis,
            fundamental_analysis,
            sentiment_analysis,
            risk_assessment,
        )
        return self._chat_completion(prompt=prompt, context=context)

    def repair_portfolio_manager(
        self,
        prompt: str,
        context: AgentContext,
        raw_output_text: str,
        error_message: str,
    ) -> AgentProviderResponse | None:
        _ = (raw_output_text, error_message)
        return self._chat_completion(prompt=prompt, context=context)
