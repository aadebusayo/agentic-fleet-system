from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass
class TaskNode:
    node_id: str
    capability: str
    requires_confirmation: bool = False


@dataclass
class TaskGraph:
    trace_id: str
    intent: str
    nodes: list[TaskNode]


class ConversationOrchestrator:
    def select_llm_profile(self, intent: str) -> str:
        mapping = {
            "deployment": "deployment",
            "analysis": "analysis",
            "general_assistance": "general",
        }
        return mapping.get(intent, "general")

    def classify_intent(self, message: str) -> str:
        msg = message.lower()
        if "deploy" in msg:
            return "deployment"
        if "analyze" in msg or "investigate" in msg:
            return "analysis"
        return "general_assistance"

    def fill_slots(self, message: str) -> dict[str, str]:
        return {"raw": message}

    def plan_task_graph(self, intent: str, slots: dict[str, str]) -> TaskGraph:
        trace_id = str(uuid4())
        nodes = [TaskNode(node_id="n1", capability="intent-validation")]
        if intent == "deployment":
            nodes.append(TaskNode(node_id="n2", capability="policy-precheck", requires_confirmation=True))
            nodes.append(TaskNode(node_id="n3", capability="deploy-execution", requires_confirmation=True))
        else:
            nodes.append(TaskNode(node_id="n2", capability="knowledge-retrieval"))
            nodes.append(TaskNode(node_id="n3", capability="response-synthesis"))
        return TaskGraph(trace_id=trace_id, intent=intent, nodes=nodes)

    def enforce_precheck_guardrails(self, graph: TaskGraph, confirmed: bool) -> None:
        if any(node.requires_confirmation for node in graph.nodes) and not confirmed:
            raise PermissionError("Confirmation required for one or more graph nodes")

    def route_to_agent(self, graph: TaskGraph) -> list[dict[str, str]]:
        profile = self.select_llm_profile(graph.intent)
        return [
            {
                "nodeId": node.node_id,
                "targetAgent": "agent-fleet-router",
                "capability": node.capability,
                "llmProfile": profile,
            }
            for node in graph.nodes
        ]
