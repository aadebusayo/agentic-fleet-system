import pytest

from backend.conversation_orchestrator import ConversationOrchestrator


def test_classify_intent_deployment() -> None:
    orchestrator = ConversationOrchestrator()
    assert orchestrator.classify_intent("Please deploy this service") == "deployment"


def test_precheck_guardrail_requires_confirmation() -> None:
    orchestrator = ConversationOrchestrator()
    graph = orchestrator.plan_task_graph("deployment", {"raw": "deploy"})
    with pytest.raises(PermissionError):
        orchestrator.enforce_precheck_guardrails(graph, confirmed=False)


def test_route_generation() -> None:
    orchestrator = ConversationOrchestrator()
    graph = orchestrator.plan_task_graph("analysis", {"raw": "analyze logs"})
    routes = orchestrator.route_to_agent(graph)
    assert len(routes) == len(graph.nodes)
    assert routes[0]["targetAgent"] == "agent-fleet-router"
    assert routes[0]["llmProfile"] == "analysis"


def test_llm_profile_fallback() -> None:
    orchestrator = ConversationOrchestrator()
    assert orchestrator.select_llm_profile("unknown-intent") == "general"
