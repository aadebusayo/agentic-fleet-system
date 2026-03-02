import pytest

from sandbox_agent.llm import (
    AnthropicClient,
    AzureOpenAIClient,
    FailoverLLMClient,
    GeminiClient,
    LLMSettings,
    LocalEndpointClient,
    OpenAICompatibleClient,
    StubLLMClient,
    build_provider_client,
    build_llm_client,
)


def make_settings(provider: str) -> LLMSettings:
    return LLMSettings(
        provider=provider,
        failover_enabled=False,
        failover_chain="openai-compatible,azure-openai,anthropic,gemini,local-endpoint",
        model="test-model",
        temperature=0.2,
        max_tokens=128,
        timeout_seconds=10,
        endpoint="https://example.test",
        api_key="test-key",
        azure_endpoint="https://example.openai.azure.com",
        azure_api_key="test-key",
        azure_deployment="test-deployment",
        azure_api_version="2024-06-01",
        anthropic_endpoint="https://api.anthropic.com/v1/messages",
        anthropic_api_key="test-key",
        anthropic_version="2023-06-01",
        gemini_endpoint=None,
        gemini_api_key="test-key",
        local_llm_endpoint="http://localhost:11434/api/chat",
        local_llm_format="openai-compatible",
        local_llm_api_key=None,
    )


def test_client_factory_supports_main_providers() -> None:
    assert isinstance(build_provider_client(make_settings("openai-compatible"), "openai-compatible"), OpenAICompatibleClient)
    assert isinstance(build_provider_client(make_settings("azure-openai"), "azure-openai"), AzureOpenAIClient)
    assert isinstance(build_provider_client(make_settings("anthropic"), "anthropic"), AnthropicClient)
    assert isinstance(build_provider_client(make_settings("gemini"), "gemini"), GeminiClient)
    assert isinstance(build_provider_client(make_settings("local-endpoint"), "local-endpoint"), LocalEndpointClient)
    assert isinstance(build_provider_client(make_settings("stub"), "stub"), StubLLMClient)


def test_build_llm_client_returns_failover_when_enabled() -> None:
    settings = make_settings("openai-compatible")
    settings.failover_enabled = True
    settings.failover_chain = "openai-compatible,local-endpoint"
    assert isinstance(build_llm_client(settings), FailoverLLMClient)


def test_validate_azure_requirements() -> None:
    settings = make_settings("azure-openai")
    settings.azure_deployment = None
    with pytest.raises(RuntimeError):
        settings.validate()


def test_validate_anthropic_requirements() -> None:
    settings = make_settings("anthropic")
    settings.anthropic_api_key = None
    with pytest.raises(RuntimeError):
        settings.validate()


def test_validate_gemini_requirements() -> None:
    settings = make_settings("gemini")
    settings.gemini_api_key = None
    with pytest.raises(RuntimeError):
        settings.validate()


def test_validate_local_endpoint_requirements() -> None:
    settings = make_settings("local-endpoint")
    settings.local_llm_endpoint = None
    with pytest.raises(RuntimeError):
        settings.validate()


def test_validate_local_format_requirements() -> None:
    settings = make_settings("local-endpoint")
    settings.local_llm_format = "unknown-format"
    with pytest.raises(RuntimeError):
        settings.validate()


def test_failover_validate_requires_one_configured_provider() -> None:
    settings = make_settings("openai-compatible")
    settings.failover_enabled = True
    settings.failover_chain = "azure-openai,local-endpoint"
    settings.azure_endpoint = None
    settings.azure_api_key = None
    settings.azure_deployment = None
    settings.local_llm_endpoint = None
    with pytest.raises(RuntimeError):
        settings.validate()
