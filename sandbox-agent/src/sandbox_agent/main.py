import os

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .gateway import StatelessAgentRuntime


app = FastAPI(title="sandbox-agent", version="0.1.0")
runtime = StatelessAgentRuntime(max_depth=3)
control_plane_base_url = os.getenv("CONTROL_PLANE_BASE_URL", "http://localhost:8081")


async def emit_monitor_event(
    event_type: str,
    message: str,
    *,
    trace_id: str | None = None,
    agent_id: str | None = None,
    health: str | None = None,
) -> None:
    payload: dict[str, str] = {
        "module": "sandbox-agent",
        "type": event_type,
        "message": message,
    }
    if trace_id is not None:
        payload["traceId"] = trace_id
    if agent_id is not None:
        payload["agentId"] = agent_id
    if health is not None:
        payload["health"] = health
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            await client.post(f"{control_plane_base_url}/monitor/events", json=payload)
    except Exception:
        pass


class ExecuteRequest(BaseModel):
    traceId: str
    task: dict


class SpawnRequest(BaseModel):
    traceId: str
    agentType: str
    payload: dict
    depth: int


@app.post("/execute")
async def execute(request: ExecuteRequest) -> dict:
    await emit_monitor_event("execute-started", "Sandbox execution started", trace_id=request.traceId, health="healthy")
    try:
        result = await runtime.execute_task(request.task, request.traceId)
        await emit_monitor_event("execute-completed", "Sandbox execution completed", trace_id=request.traceId, health="healthy")
        return result
    except Exception as exc:
        await emit_monitor_event("execute-failed", str(exc), trace_id=request.traceId, health="degraded")
        raise


@app.post("/spawn")
async def spawn(request: SpawnRequest) -> dict:
    try:
        result = await runtime.spawn_sub_agent(request.agentType, request.payload, request.depth)
        await emit_monitor_event(
            "agent-spawned",
            f"Sandbox spawned sub-agent type={request.agentType}",
            trace_id=request.traceId,
            agent_id=f"sandbox-{request.agentType}",
            health="healthy",
        )
        return result
    except RuntimeError as exc:
        await emit_monitor_event(
            "agent-spawn-blocked",
            str(exc),
            trace_id=request.traceId,
            agent_id=f"sandbox-{request.agentType}",
            health="degraded",
        )
        raise HTTPException(status_code=429, detail=str(exc)) from exc
