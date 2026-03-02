# Architecture Overview

## 1. Logical Planes

### Backend Orchestrator

- Receives user/session requests.
- Performs intent classification and slot filling.
- Builds a task graph (DAG) with safety checkpoints.
- Routes graph nodes to agent fleet via control plane.

### Control Plane

- Enforces authentication, authorization, and policy constraints.
- Proxies operation and tool execution.
- Applies rate and budget limits.
- Maintains immutable audit events.
- Brokers inter-agent A2A communication and trace propagation.

### Agent Fleet Supervisor

- Manages agent registry and capability bindings.
- Spawns and retires agents under policy.
- Enforces recursion/delegation limits and execution caps.
- Monitors health and reports availability to orchestrator/control plane.

### Sandboxed Agent Execution

- Executes constrained workloads in a stateless pattern.
- Requests tool execution through control plane only.
- Supports dynamic task payloads and sub-agent stub workflows.

## 2. Control and Data Flow

1. Request enters backend orchestrator.
2. Orchestrator generates DAG and node execution plan.
3. Every operation request is validated by control plane policy engine.
4. Control plane forwards approved work to fleet supervisor.
5. Supervisor schedules sandbox agents.
6. Sandbox agents execute and report status/checkpoints.
7. State/memory updates and audit trails are persisted with shared trace IDs.

## 3. Protocols

- A2A protocol: peer agent messages, task delegation, status updates.
- MCP protocol: tool and context exchange contract.
- Capability discovery: manifests + schema validation.

## 4. Distributed State and Memory

Shared state model tracks:

- session context propagation
- task graph checkpoints
- intermediate memory and outputs
- trace spans and audit evidence

Implementations can bind to Redis, Postgres, Cosmos DB, etc., behind stable interfaces in `shared/state`.

## 5. Guardrails

- Semantic and schema validation at ingestion and before tool invocation.
- Recursion/delegation hard limits in fleet supervisor.
- Per-agent budget/execution limits in control plane.
- Mandatory human confirmation hooks for high-risk operations.

## 6. Deployment Model

- Cloud-agnostic deployment via Terraform modules.
- Isolated networking, load balancing, secret stores, and observability primitives.
- CI/CD enforces tests, security scanning, IaC validation, and staged deployment.
