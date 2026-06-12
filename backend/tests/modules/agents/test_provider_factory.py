import pytest

from app.core.config import Settings
from app.modules.agents.errors import AgentProviderConfigurationError
from app.modules.agents.provider_factory import create_scads_agent_provider
from app.modules.agents.scads_provider import ScadsAIAgentProvider


def test_create_scads_provider_requires_enabled_provider() -> None:
    with pytest.raises(AgentProviderConfigurationError):
        create_scads_agent_provider(Settings(scadsai_llm_enabled=False), None)


def test_create_scads_provider_rejects_disallowed_model() -> None:
    settings = Settings(scadsai_llm_enabled=True, scadsai_api_key="key")

    with pytest.raises(AgentProviderConfigurationError):
        create_scads_agent_provider(settings, "not-allowed")


def test_create_scads_provider_returns_provider_for_allowed_model() -> None:
    settings = Settings(scadsai_llm_enabled=True, scadsai_api_key="key")

    provider = create_scads_agent_provider(
        settings,
        "meta-llama/Llama-3.3-70B-Instruct",
    )

    assert isinstance(provider, ScadsAIAgentProvider)


def test_settings_requires_scads_key_only_when_enabled() -> None:
    Settings(scadsai_llm_enabled=False, scadsai_api_key=None)

    with pytest.raises(ValueError):
        Settings(scadsai_llm_enabled=True, scadsai_api_key=None)
