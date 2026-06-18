import json
from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.domain.enums import AgentMode
from app.modules.agents.errors import AgentProviderError
from app.modules.agents.scads_provider import ScadsAIAgentProvider
from app.modules.agents.types import AgentContext
from app.modules.market_data.provider import DailyBar


def _context() -> AgentContext:
    bar = DailyBar(
        date=date(2026, 1, 2),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        adjusted_close=Decimal("100"),
        volume=Decimal("1000"),
        raw={},
    )
    return AgentContext(
        experiment_id=1,
        execution_step_id=2,
        symbol="SPY",
        bar=bar,
        cash=Decimal("10000"),
        position_quantity=Decimal("0"),
        current_portfolio_value=Decimal("10000"),
        confidence_threshold=None,
        parameters_json=None,
        agent_mode=AgentMode.SINGLE_AGENT,
        model_name="meta-llama/Llama-3.3-70B-Instruct",
    )


def test_scads_provider_posts_openai_compatible_request() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "model": "meta-llama/Llama-3.3-70B-Instruct",
                "choices": [
                    {
                        "message": {
                            "content": '{"action":"HOLD","confidence":0,"rationale":"test"}'
                        }
                    }
                ],
            },
        )

    provider = ScadsAIAgentProvider(
        api_key="secret-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = provider.complete("prompt", _context())

    assert response.raw_output_text == '{"action":"HOLD","confidence":0,"rationale":"test"}'
    assert requests[0].url.path == "/v1/chat/completions"
    assert requests[0].headers["authorization"] == "Bearer secret-key"
    payload = json.loads(requests[0].read().decode())
    assert payload["model"] == "meta-llama/Llama-3.3-70B-Instruct"
    assert "tools" not in payload


@pytest.mark.parametrize("status_code", [401, 403, 429, 500])
def test_scads_provider_http_errors_raise_provider_error(status_code: int) -> None:
    provider = ScadsAIAgentProvider(
        api_key="secret-key",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(status_code, text="failed")
            )
        ),
    )

    with pytest.raises(AgentProviderError):
        provider.complete("prompt", _context())


def test_scads_provider_malformed_response_raises_provider_error() -> None:
    provider = ScadsAIAgentProvider(
        api_key="secret-key",
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))
        ),
    )

    with pytest.raises(AgentProviderError):
        provider.complete("prompt", _context())
