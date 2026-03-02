from __future__ import annotations

from typing import Protocol, Any

from .llm import LLMSettings, build_llm_client


class AgentGateway(Protocol):
    async def invoke_llm(self, prompt: str, context: dict[str, Any]) -> str: ...

    async def execute_task(self, task: dict[str, Any], trace_id: str) -> dict[str, Any]: ...

    async def spawn_sub_agent(self, agent_type: str, payload: dict[str, Any], depth: int) -> dict[str, Any]: ...


class StatelessAgentRuntime:
    def __init__(self, max_depth: int = 3) -> None:
        self.max_depth = max_depth
        settings = LLMSettings.from_env()
        settings.validate()
        self.llm_settings = settings
        self.llm_client = build_llm_client(settings)

    async def invoke_llm(self, prompt: str, context: dict[str, Any]) -> str:
        return await self.llm_client.complete(prompt, context)

    async def execute_task(self, task: dict[str, Any], trace_id: str) -> dict[str, Any]:
        llm_output = None
        if "prompt" in task:
            llm_output = await self.invoke_llm(str(task["prompt"]), {"traceId": trace_id})
        return {
            "traceId": trace_id,
            "status": "completed",
            "result": {
                "echo": task,
                "llm": llm_output,
                "model": self.llm_settings.model,
                "provider": self.llm_settings.provider,
            },
        }

    async def spawn_sub_agent(self, agent_type: str, payload: dict[str, Any], depth: int) -> dict[str, Any]:
        if depth > self.max_depth:
            raise RuntimeError("sub-agent recursion limit exceeded")
        return {
            "spawned": True,
            "agentType": agent_type,
            "payload": payload,
            "depth": depth,
        }
