from app.core.config import Settings
from app.modules.agents.errors import AgentProviderConfigurationError
from app.modules.agents.fake_provider import FakeAgentProvider
from app.modules.agents.scads_provider import (
    ScadsAIAgentProvider,
    ScadsAIPipelineProvider,
)
from app.modules.agents.types import AgentProvider
from app.modules.agents.pipeline_types import PipelineProvider


def create_historical_agent_provider() -> AgentProvider:
    return FakeAgentProvider()


def create_scads_agent_provider(settings: Settings, model_name: str | None) -> AgentProvider:
    _validated_model(settings, model_name)
    return ScadsAIAgentProvider(
        api_key=settings.scadsai_api_key or "",
        base_url=settings.scadsai_base_url,
        timeout_seconds=settings.scadsai_request_timeout_seconds,
    )


def create_scads_pipeline_provider(
    settings: Settings, model_name: str | None
) -> PipelineProvider:
    _validated_model(settings, model_name)
    return ScadsAIPipelineProvider(
        api_key=settings.scadsai_api_key or "",
        base_url=settings.scadsai_base_url,
        timeout_seconds=settings.scadsai_request_timeout_seconds,
    )


def _validated_model(settings: Settings, model_name: str | None) -> str:
    if not settings.scadsai_llm_enabled:
        raise AgentProviderConfigurationError(
            "ScaDS.AI LLM provider is disabled.",
            details={"requiredConfig": "SCADSAI_LLM_ENABLED=true"},
        )
    if not settings.scadsai_api_key:
        raise AgentProviderConfigurationError(
            "ScaDS.AI API key is required.",
            details={"requiredConfig": "SCADSAI_API_KEY"},
        )
    selected_model = model_name or settings.scadsai_default_model
    allowed_models = settings.scadsai_allowed_model_list
    if selected_model not in allowed_models:
        raise AgentProviderConfigurationError(
            "Selected ScaDS.AI model is not allowed.",
            details={"modelName": selected_model, "allowedModels": allowed_models},
        )
    return selected_model
