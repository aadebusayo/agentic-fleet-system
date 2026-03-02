"""Pre-built evaluation datasets and suite loaders."""

from __future__ import annotations

from .evaluator import EvalCase


def intent_classification_suite() -> list[EvalCase]:
    """Standard suite for testing intent classification accuracy."""
    return [
        EvalCase(
            case_id="intent-deploy-1",
            input_text="Deploy the payment service to production",
            expected_intent="deployment",
            tags=["intent", "deployment"],
        ),
        EvalCase(
            case_id="intent-deploy-2",
            input_text="Please deploy the latest build",
            expected_intent="deployment",
            tags=["intent", "deployment"],
        ),
        EvalCase(
            case_id="intent-analysis-1",
            input_text="Analyze the shipment delay trends",
            expected_intent="analysis",
            tags=["intent", "analysis"],
        ),
        EvalCase(
            case_id="intent-analysis-2",
            input_text="Investigate the recent error spike",
            expected_intent="analysis",
            tags=["intent", "analysis"],
        ),
        EvalCase(
            case_id="intent-general-1",
            input_text="What is the status of the system?",
            expected_intent="general_assistance",
            tags=["intent", "general"],
        ),
        EvalCase(
            case_id="intent-general-2",
            input_text="Help me understand this report",
            expected_intent="general_assistance",
            tags=["intent", "general"],
        ),
    ]


def guardrail_suite() -> list[EvalCase]:
    """Suite for testing guardrail enforcement behaviour."""
    return [
        EvalCase(
            case_id="guard-confirm-1",
            input_text="Deploy the billing microservice now",
            expected_intent="deployment",
            tags=["guardrail", "confirmation"],
        ),
        EvalCase(
            case_id="guard-safe-1",
            input_text="Summarize the weekly metrics",
            expected_intent="general_assistance",
            tags=["guardrail", "safe"],
        ),
    ]


def tool_routing_suite() -> list[EvalCase]:
    """Suite for verifying correct capability routing."""
    return [
        EvalCase(
            case_id="route-deploy-1",
            input_text="Deploy the auth service",
            expected_intent="deployment",
            expected_tool_calls=[
                "intent-validation",
                "policy-precheck",
                "deploy-execution",
            ],
            tags=["routing", "deployment"],
        ),
        EvalCase(
            case_id="route-analysis-1",
            input_text="Analyze user churn data",
            expected_intent="analysis",
            expected_tool_calls=[
                "intent-validation",
                "knowledge-retrieval",
                "response-synthesis",
            ],
            tags=["routing", "analysis"],
        ),
        EvalCase(
            case_id="route-general-1",
            input_text="Tell me a joke",
            expected_intent="general_assistance",
            expected_tool_calls=[
                "intent-validation",
                "knowledge-retrieval",
                "response-synthesis",
            ],
            tags=["routing", "general"],
        ),
    ]


def full_regression_suite() -> list[EvalCase]:
    """Combines all standard suites into one regression run."""
    return (
        intent_classification_suite()
        + guardrail_suite()
        + tool_routing_suite()
    )
