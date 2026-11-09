import pytest

from backend.app.config import settings
from backend.app.llm_client import LLMClient


@pytest.mark.integration
def test_live_llm_provider_deployment():
    """Live probe asserting LLM credentials, network reachability, and model deployment validity."""
    if not settings.llm_api_key:
        pytest.fail(
            "LLM_API_KEY is not configured. Live integration tests require valid credentials."
        )

    client = LLMClient(
        api_key=settings.llm_api_key,
        api_url=settings.llm_api_url,
        model=settings.llm_model,
    )

    # Minimal probe to verify authentication and active deployment
    response = client.generate(
        "SYSTEM:\nYou are a ping responder.\nUSER:\nSay pong", max_tokens=100
    )

    assert isinstance(response, str)
    assert len(response.strip()) > 0
