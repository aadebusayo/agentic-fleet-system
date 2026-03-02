"""Metric computation helpers for evaluation runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .evaluator import EvalCaseResult


@dataclass
class MetricResult:
    """Uniform container for a single computed metric."""

    name: str
    value: float
    unit: str = ""
    details: dict[str, float] = field(default_factory=dict)


# ------------------------------------------------------------------
# Intent accuracy
# ------------------------------------------------------------------

def compute_accuracy(pairs: list[tuple[str | None, str | None]]) -> MetricResult:
    """Compute exact-match accuracy between expected and actual values."""
    if not pairs:
        return MetricResult(name="accuracy", value=0.0, unit="ratio")

    matches = sum(1 for expected, actual in pairs if expected == actual)
    total = len(pairs)
    return MetricResult(
        name="accuracy",
        value=round(matches / total, 4),
        unit="ratio",
        details={"matches": float(matches), "total": float(total)},
    )


# ------------------------------------------------------------------
# Latency
# ------------------------------------------------------------------

def compute_latency_stats(latencies: list[float]) -> MetricResult:
    """Compute p50, p90, p99, min, max, and mean latency."""
    if not latencies:
        return MetricResult(name="latency", value=0.0, unit="ms")

    sorted_lat = sorted(latencies)
    n = len(sorted_lat)

    def percentile(p: float) -> float:
        idx = int(p / 100 * (n - 1))
        return round(sorted_lat[idx], 2)

    mean_val = round(sum(sorted_lat) / n, 2)
    return MetricResult(
        name="latency",
        value=mean_val,
        unit="ms",
        details={
            "min": sorted_lat[0],
            "max": sorted_lat[-1],
            "mean": mean_val,
            "p50": percentile(50),
            "p90": percentile(90),
            "p99": percentile(99),
            "count": float(n),
        },
    )


# ------------------------------------------------------------------
# Token efficiency
# ------------------------------------------------------------------

def compute_token_efficiency(token_counts: list[int]) -> MetricResult:
    """Compute average and total token usage across eval cases."""
    if not token_counts:
        return MetricResult(name="token_efficiency", value=0.0, unit="tokens")

    total = sum(token_counts)
    avg = round(total / len(token_counts), 2)
    return MetricResult(
        name="token_efficiency",
        value=avg,
        unit="tokens/case",
        details={
            "total_tokens": float(total),
            "avg_tokens": avg,
            "min_tokens": float(min(token_counts)),
            "max_tokens": float(max(token_counts)),
            "case_count": float(len(token_counts)),
        },
    )


# ------------------------------------------------------------------
# Tool call success rate
# ------------------------------------------------------------------

def compute_tool_success_rate(
    pairs: list[tuple[list[str], list[str]]],
) -> MetricResult:
    """Compute the ratio of correctly invoked tool calls."""
    if not pairs:
        return MetricResult(name="tool_success_rate", value=0.0, unit="ratio")

    total_expected = 0
    total_matched = 0
    for expected, actual in pairs:
        expected_set = set(expected)
        actual_set = set(actual)
        total_expected += len(expected_set)
        total_matched += len(expected_set & actual_set)

    value = round(total_matched / total_expected, 4) if total_expected else 1.0
    return MetricResult(
        name="tool_success_rate",
        value=value,
        unit="ratio",
        details={
            "total_expected": float(total_expected),
            "total_matched": float(total_matched),
        },
    )


# ------------------------------------------------------------------
# Guardrail compliance
# ------------------------------------------------------------------

def compute_guardrail_compliance(results: list["EvalCaseResult"]) -> MetricResult:
    """Compute the fraction of cases that passed all guardrails."""
    if not results:
        return MetricResult(name="guardrail_compliance", value=1.0, unit="ratio")

    passed = sum(1 for r in results if r.guardrail_passed)
    total = len(results)
    return MetricResult(
        name="guardrail_compliance",
        value=round(passed / total, 4),
        unit="ratio",
        details={"passed": float(passed), "total": float(total)},
    )
