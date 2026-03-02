import json
import os
from datetime import datetime, timezone
from urllib import request as urllib_request

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .conversation_orchestrator import ConversationOrchestrator
from .evaluation.evaluator import Evaluator, EvalCase
from .evaluation import datasets as eval_datasets


app = FastAPI(title="backend-orchestrator", version="0.1.0")
orchestrator = ConversationOrchestrator()
evaluator = Evaluator(orchestrator=orchestrator)
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


# ------------------------------------------------------------------
# Evaluation & model performance endpoints
# ------------------------------------------------------------------


class EvalCaseRequest(BaseModel):
    case_id: str
    input_text: str
    expected_intent: str | None = None
    expected_output: str | None = None
    expected_tool_calls: list[str] | None = None
    tags: list[str] = []


class EvalRunRequest(BaseModel):
    suite_name: str
    model: str = ""
    provider: str = ""
    cases: list[EvalCaseRequest] = []


@app.post("/eval/run")
def run_evaluation(request: EvalRunRequest) -> dict:
    """Run an evaluation suite with custom cases."""
    emit_monitor_event("eval-started", f"Evaluation suite '{request.suite_name}' started", health="healthy")
    cases = [
        EvalCase(
            case_id=c.case_id,
            input_text=c.input_text,
            expected_intent=c.expected_intent,
            expected_output=c.expected_output,
            expected_tool_calls=c.expected_tool_calls,
            tags=c.tags,
        )
        for c in request.cases
    ]
    result = evaluator.run_suite(
        request.suite_name,
        cases,
        model=request.model,
        provider=request.provider,
    )
    emit_monitor_event(
        "eval-completed",
        f"Evaluation '{request.suite_name}' completed: {result.status.value}",
        health="healthy",
    )
    return {
        "runId": result.run_id,
        "suiteName": result.suite_name,
        "status": result.status.value,
        "startedAt": result.started_at,
        "completedAt": result.completed_at,
        "model": result.model,
        "provider": result.provider,
        "caseResults": [
            {
                "caseId": cr.case_id,
                "actualIntent": cr.actual_intent,
                "actualOutput": cr.actual_output,
                "actualToolCalls": cr.actual_tool_calls,
                "latencyMs": cr.latency_ms,
                "tokenCount": cr.token_count,
                "guardrailPassed": cr.guardrail_passed,
                "error": cr.error,
            }
            for cr in result.case_results
        ],
        "metrics": {
            k: {
                "name": m.name,
                "value": m.value,
                "unit": m.unit,
                "details": m.details,
            }
            for k, m in result.metrics.items()
        },
    }


@app.post("/eval/suite/{suite_name}")
def run_builtin_suite(suite_name: str) -> dict:
    """Run a built-in evaluation suite by name.

    Available suites: intent, guardrail, routing, regression.
    """
    suite_map: dict[str, list[EvalCase]] = {
        "intent": eval_datasets.intent_classification_suite(),
        "guardrail": eval_datasets.guardrail_suite(),
        "routing": eval_datasets.tool_routing_suite(),
        "regression": eval_datasets.full_regression_suite(),
    }
    cases = suite_map.get(suite_name)
    if cases is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown suite '{suite_name}'. Available: {', '.join(suite_map)}",
        )
    emit_monitor_event("eval-builtin-started", f"Built-in suite '{suite_name}' started", health="healthy")
    result = evaluator.run_suite(suite_name, cases)
    return {
        "runId": result.run_id,
        "suiteName": result.suite_name,
        "status": result.status.value,
        "startedAt": result.started_at,
        "completedAt": result.completed_at,
        "caseResults": [
            {
                "caseId": cr.case_id,
                "actualIntent": cr.actual_intent,
                "actualOutput": cr.actual_output,
                "actualToolCalls": cr.actual_tool_calls,
                "latencyMs": cr.latency_ms,
                "tokenCount": cr.token_count,
                "guardrailPassed": cr.guardrail_passed,
                "error": cr.error,
            }
            for cr in result.case_results
        ],
        "metrics": {
            k: {
                "name": m.name,
                "value": m.value,
                "unit": m.unit,
                "details": m.details,
            }
            for k, m in result.metrics.items()
        },
    }


@app.get("/eval/suites")
def list_builtin_suites() -> dict:
    """List available built-in evaluation suites."""
    return {
        "suites": [
            {"name": "intent", "description": "Intent classification accuracy", "cases": len(eval_datasets.intent_classification_suite())},
            {"name": "guardrail", "description": "Guardrail enforcement behaviour", "cases": len(eval_datasets.guardrail_suite())},
            {"name": "routing", "description": "Capability routing correctness", "cases": len(eval_datasets.tool_routing_suite())},
            {"name": "regression", "description": "Full regression (all suites combined)", "cases": len(eval_datasets.full_regression_suite())},
        ]
    }
