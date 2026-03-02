# ADR 0002: Control Plane as Mandatory Policy and Audit Boundary

## Status

Accepted

## Context

Direct tool execution from agents increases risk and weakens auditability.

## Decision

All tool and operation invocations must pass through control plane authorization and logging.

## Consequences

- Higher trust and compliance posture.
- Slight increase in latency due to policy checks.
