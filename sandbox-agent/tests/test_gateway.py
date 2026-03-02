import pytest

from sandbox_agent.gateway import StatelessAgentRuntime
from sandbox_agent.llm import LLMSettings


@pytest.mark.asyncio
async def test_spawn_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_LLM_PROVIDER", "stub")
    monkeypatch.setenv("AGENT_ALLOW_STUB_LLM", "true")
    monkeypatch.setenv("AGENT_LLM_FAILOVER_ENABLED", "false")
    runtime = StatelessAgentRuntime(max_depth=1)
    with pytest.raises(RuntimeError):
        await runtime.spawn_sub_agent("analysis", {}, 2)


@pytest.mark.asyncio
async def test_execute_task_returns_llm_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_LLM_PROVIDER", "stub")
    monkeypatch.setenv("AGENT_ALLOW_STUB_LLM", "true")
    monkeypatch.setenv("AGENT_LLM_FAILOVER_ENABLED", "false")
    monkeypatch.setenv("AGENT_LLM_MODEL", "test-model")
    runtime = StatelessAgentRuntime(max_depth=2)
    result = await runtime.execute_task({"prompt": "hello world"}, "trace-abc")
    assert result["result"]["provider"] == "stub"
    assert result["result"]["model"] == "test-model"
    assert isinstance(result["result"]["llm"], str)


def test_llm_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENT_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("AGENT_LLM_MODEL", raising=False)
    settings = LLMSettings.from_env()
    assert settings.provider == "openai-compatible"
    assert settings.model == "gpt-4o-mini"
