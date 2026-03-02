"""Core evaluation engine for agent and model performance assessment.

Lives inside the backend because it evaluates the orchestrator pipeline
directly — intent classification, slot filling, routing, guardrails, and
end-to-end latency — without needing a network hop.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from ..conversation_orchestrator import ConversationOrchestrator

from .metrics import (
    MetricResult,
    compute_accuracy,
    compute_latency_stats,
    compute_token_efficiency,
    compute_tool_success_rate,
    compute_guardrail_compliance,
)


class EvalStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class EvalCase:
    """A single evaluation test case."""

    case_id: str
    input_text: str
    expected_intent: str | None = None
    expected_output: str | None = None
    expected_tool_calls: list[str] | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class EvalCaseResult:
    """Result of running a single eval case."""

    case_id: str
    actual_intent: str | None = None
    actual_output: str | None = None
    actual_tool_calls: list[str] | None = None
    latency_ms: float = 0.0
    token_count: int = 0
    guardrail_passed: bool = True
    error: str | None = None


@dataclass
class EvalRunResult:
    """Aggregate result for a full evaluation run."""

    run_id: str
    suite_name: str
    status: EvalStatus
    started_at: str
    completed_at: str | None = None
    model: str = ""
    provider: str = ""
    case_results: list[EvalCaseResult] = field(default_factory=list)
    metrics: dict[str, MetricResult] = field(default_factory=dict)


class Evaluator:
    """Orchestrates evaluation runs against the backend pipeline."""

    def __init__(self, orchestrator: ConversationOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator or ConversationOrchestrator()

    def create_run(self, suite_name: str, model: str = "", provider: str = "") -> EvalRunResult:
        """Initialize an evaluation run."""
        return EvalRunResult(
            run_id=str(uuid4()),
            suite_name=suite_name,
            status=EvalStatus.PENDING,
            started_at=datetime.now(timezone.utc).isoformat(),
            model=model,
            provider=provider,
        )

    def execute_case(self, case: EvalCase) -> EvalCaseResult:
        """Execute a single eval case through the live orchestrator pipeline."""
        start = time.perf_counter()
        try:
            intent = self.orchestrator.classify_intent(case.input_text)
            slots = self.orchestrator.fill_slots(case.input_text)
            graph = self.orchestrator.plan_task_graph(intent, slots)

            guardrail_passed = True
            try:
                self.orchestrator.enforce_precheck_guardrails(graph, confirmed=True)
            except PermissionError:
                guardrail_passed = False

            routes = self.orchestrator.route_to_agent(graph)
            elapsed = (time.perf_counter() - start) * 1000

            return EvalCaseResult(
                case_id=case.case_id,
                actual_intent=intent,
                actual_output=f"routes={len(routes)}",
                actual_tool_calls=[r["capability"] for r in routes],
                latency_ms=round(elapsed, 2),
                token_count=0,
                guardrail_passed=guardrail_passed,
            )
        except Exception as exc:  # noqa: BLE001
            elapsed = (time.perf_counter() - start) * 1000
            return EvalCaseResult(
                case_id=case.case_id,
                latency_ms=round(elapsed, 2),
                error=str(exc),
            )

    def run_suite(
        self,
        suite_name: str,
        cases: list[EvalCase],
        *,
        model: str = "",
        provider: str = "",
    ) -> EvalRunResult:
        """Run a full evaluation suite and compute aggregate metrics."""
        run = self.create_run(suite_name, model=model, provider=provider)
        run.status = EvalStatus.RUNNING

        for case in cases:
            result = self.execute_case(case)
            run.case_results.append(result)

        run.metrics = self._compute_metrics(cases, run.case_results)
        run.status = EvalStatus.COMPLETED
        run.completed_at = datetime.now(timezone.utc).isoformat()
        return run

    # ------------------------------------------------------------------
    # Metric aggregation
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_metrics(
        cases: list[EvalCase],
        results: list[EvalCaseResult],
    ) -> dict[str, MetricResult]:
        metrics: dict[str, MetricResult] = {}

        # Intent accuracy
        intent_pairs = [
            (c.expected_intent, r.actual_intent)
            for c, r in zip(cases, results)
            if c.expected_intent is not None
        ]
        if intent_pairs:
            metrics["intent_accuracy"] = compute_accuracy(intent_pairs)

        # Latency
        latencies = [r.latency_ms for r in results if r.error is None]
        if latencies:
            metrics["latency"] = compute_latency_stats(latencies)

        # Token efficiency
        token_counts = [r.token_count for r in results if r.error is None]
        if token_counts:
            metrics["token_efficiency"] = compute_token_efficiency(token_counts)

        # Tool call success rate
        tool_pairs = [
            (c.expected_tool_calls or [], r.actual_tool_calls or [])
            for c, r in zip(cases, results)
            if c.expected_tool_calls is not None
        ]
        if tool_pairs:
            metrics["tool_success_rate"] = compute_tool_success_rate(tool_pairs)

        # Guardrail compliance
        metrics["guardrail_compliance"] = compute_guardrail_compliance(results)

        return metrics
