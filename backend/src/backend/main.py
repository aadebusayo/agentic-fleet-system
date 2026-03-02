import json
import os
from datetime import datetime, timezone
from urllib import request as urllib_request

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .conversation_orchestrator import ConversationOrchestrator


app = FastAPI(title="backend-orchestrator", version="0.1.0")
orchestrator = ConversationOrchestrator()
control_plane_base_url = os.getenv("CONTROL_PLANE_BASE_URL", "http://localhost:8081")
cors_origins = os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:8081").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def emit_monitor_event(event_type: str, message: str, *, trace_id: str | None = None, health: str | None = None) -> None:
    payload: dict[str, str] = {
        "module": "backend",
        "type": event_type,
        "message": message,
    }
    if trace_id is not None:
        payload["traceId"] = trace_id
    if health is not None:
        payload["health"] = health
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            f"{control_plane_base_url}/monitor/events",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib_request.urlopen(req, timeout=1.5).read()
    except Exception:
        pass


class OrchestrateRequest(BaseModel):
    message: str
    confirmed: bool = False


@app.post("/orchestrate")
def orchestrate(request: OrchestrateRequest) -> dict:
    emit_monitor_event("request-received", "Backend received orchestration request", health="healthy")
    intent = orchestrator.classify_intent(request.message)
    slots = orchestrator.fill_slots(request.message)
    graph = orchestrator.plan_task_graph(intent, slots)
    emit_monitor_event("graph-planned", f"Task graph planned for intent={intent}", trace_id=graph.trace_id, health="healthy")
    try:
        orchestrator.enforce_precheck_guardrails(graph, request.confirmed)
    except PermissionError as exc:
        emit_monitor_event("guardrail-blocked", str(exc), trace_id=graph.trace_id, health="degraded")
        raise HTTPException(status_code=412, detail=str(exc)) from exc
    routes = orchestrator.route_to_agent(graph)
    emit_monitor_event("routes-generated", f"Generated {len(routes)} route(s)", trace_id=graph.trace_id, health="healthy")
    return {
        "traceId": graph.trace_id,
        "intent": graph.intent,
        "routes": routes,
    }
