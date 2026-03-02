import pytest

from backend.evaluation.evaluator import Evaluator, EvalCase, EvalStatus
from backend.evaluation.metrics import (
    MetricResult,
    compute_accuracy,
    compute_latency_stats,
    compute_token_efficiency,
    compute_tool_success_rate,
    compute_guardrail_compliance,
)
from backend.evaluation.datasets import (
    intent_classification_suite,
    guardrail_suite,
    tool_routing_suite,
    full_regression_suite,
)
from backend.conversation_orchestrator import ConversationOrchestrator


# ------------------------------------------------------------------
# Metric helpers
# ------------------------------------------------------------------


def test_accuracy_perfect() -> None:
    pairs = [("a", "a"), ("b", "b"), ("c", "c")]
    result = compute_accuracy(pairs)
    assert result.value == 1.0
    assert result.details["matches"] == 3.0


def test_accuracy_partial() -> None:
    pairs = [("a", "a"), ("b", "x"), ("c", "c")]
    result = compute_accuracy(pairs)
    assert 0.6 < result.value < 0.7


def test_accuracy_empty() -> None:
    assert compute_accuracy([]).value == 0.0


def test_latency_stats() -> None:
    result = compute_latency_stats([10.0, 20.0, 30.0, 40.0, 50.0])
    assert result.name == "latency"
    assert result.details["min"] == 10.0
    assert result.details["max"] == 50.0
    assert result.details["count"] == 5.0


def test_latency_empty() -> None:
    assert compute_latency_stats([]).value == 0.0


def test_token_efficiency() -> None:
    result = compute_token_efficiency([100, 200, 300])
    assert result.value == 200.0
    assert result.details["total_tokens"] == 600.0


def test_token_efficiency_empty() -> None:
    assert compute_token_efficiency([]).value == 0.0


def test_tool_success_rate_perfect() -> None:
    pairs = [(["a", "b"], ["a", "b"]), (["c"], ["c"])]
    result = compute_tool_success_rate(pairs)
    assert result.value == 1.0


def test_tool_success_rate_partial() -> None:
    pairs = [(["a", "b"], ["a"]), (["c"], ["c"])]
    result = compute_tool_success_rate(pairs)
    assert 0.6 < result.value < 0.7


def test_tool_success_rate_empty() -> None:
    assert compute_tool_success_rate([]).value == 0.0


def test_guardrail_compliance_all_passed() -> None:
    from backend.evaluation.evaluator import EvalCaseResult

    results = [
        EvalCaseResult(case_id="1", guardrail_passed=True),
        EvalCaseResult(case_id="2", guardrail_passed=True),
    ]
    metric = compute_guardrail_compliance(results)
    assert metric.value == 1.0


def test_guardrail_compliance_mixed() -> None:
    from backend.evaluation.evaluator import EvalCaseResult

    results = [
        EvalCaseResult(case_id="1", guardrail_passed=True),
        EvalCaseResult(case_id="2", guardrail_passed=False),
    ]
    metric = compute_guardrail_compliance(results)
    assert metric.value == 0.5


# ------------------------------------------------------------------
# Evaluator engine
# ------------------------------------------------------------------


def test_evaluator_run_suite_completes() -> None:
    ev = Evaluator()
    cases = [
        EvalCase(case_id="t1", input_text="deploy the API", expected_intent="deployment"),
        EvalCase(case_id="t2", input_text="analyze logs", expected_intent="analysis"),
    ]
    run = ev.run_suite("test-suite", cases)
    assert run.status == EvalStatus.COMPLETED
    assert len(run.case_results) == 2
    assert "intent_accuracy" in run.metrics
    assert "guardrail_compliance" in run.metrics


def test_evaluator_intent_accuracy() -> None:
    ev = Evaluator()
    cases = intent_classification_suite()
    run = ev.run_suite("intent-check", cases)
    assert run.metrics["intent_accuracy"].value == 1.0, (
        "Built-in intent suite should achieve 100% with the rule-based classifier"
    )


def test_evaluator_tool_routing_accuracy() -> None:
    ev = Evaluator()
    cases = tool_routing_suite()
    run = ev.run_suite("routing-check", cases)
    assert run.metrics["tool_success_rate"].value == 1.0, (
        "Built-in routing suite should achieve 100% with deterministic planner"
    )


def test_evaluator_records_latency() -> None:
    ev = Evaluator()
    cases = [EvalCase(case_id="lat-1", input_text="deploy something")]
    run = ev.run_suite("latency-check", cases)
    assert "latency" in run.metrics
    assert run.metrics["latency"].value >= 0.0


def test_evaluator_uses_shared_orchestrator() -> None:
    orch = ConversationOrchestrator()
    ev = Evaluator(orchestrator=orch)
    assert ev.orchestrator is orch


# ------------------------------------------------------------------
# Dataset helpers
# ------------------------------------------------------------------


def test_intent_suite_not_empty() -> None:
    assert len(intent_classification_suite()) > 0


def test_guardrail_suite_not_empty() -> None:
    assert len(guardrail_suite()) > 0


def test_routing_suite_not_empty() -> None:
    assert len(tool_routing_suite()) > 0


def test_regression_suite_combines_all() -> None:
    total = (
        len(intent_classification_suite())
        + len(guardrail_suite())
        + len(tool_routing_suite())
    )
    assert len(full_regression_suite()) == total
