# ADR 0003: Recursion and Execution Budget Guardrails

## Status

Accepted

## Context

Autonomous delegation can lead to uncontrolled recursive spawning and budget exhaustion.

## Decision

Enforce hard recursion depth, delegation count, and per-trace operation budgets.

## Consequences

- Predictable execution envelope.
- Requires explicit override policy path for exceptional workflows.
