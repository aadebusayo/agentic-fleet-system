# Agent Platform Monorepo

Production-grade, domain-agnostic boilerplate for an enterprise multi-agent cognitive platform. Ready to Go.

## Repository Layout

```text
agent-platform/
  backend/            # Conversation orchestration + DAG planning (Python)
  control-plane/      # Policy, auth proxy, A2A broker (TypeScript)
  agent-fleet/        # Agent registry, spawn/delegation supervisor (Go)
  sandbox-agent/      # Sandboxed stateless execution gateway (Python)
  shared/             # Schemas, protocol contracts, state interfaces
  infra/              # Terraform modules + environment stacks
  pipelines/          # CI/CD templates and reusable pipeline fragments
  docs/adr/           # Architecture Decision Records
```

## Core Platform Capabilities

- Backend orchestrator with intent extraction, slot filling, planner, and fleet routing.
- Built-in evaluation engine with intent accuracy, latency profiling, token efficiency, tool routing, and guardrail compliance metrics.
- Control plane with policy enforcement, budget/rate limits, operation proxy, and audit logs.
- Agent fleet supervisor with registration, capability assignment, delegation limits, and health checks.
- Sandboxed execution layer with controlled tool calling and recursive sub-agent stubs.
- A2A + MCP contract support for inter-agent communication.
- Distributed memory and state abstractions with trace correlation/checkpoint metadata.

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Go 1.22+
- Terraform 1.8+

### Common Tasks

```bash
make bootstrap
make test
make lint
make security-scan
make infra-validate
```

## Local Docker Flow Test

1. Copy environment template:

```bash
cp .env.local.example .env.local
```

2. Set the provider variables you want to test in `.env.local`.

3. Run all core services locally with Docker:

```bash
docker compose -f docker-compose.local.yml --env-file .env.local up --build
```

4. Open management UI:

- Ops dashboard: `http://localhost:8081/ops`

5. Trigger a sample orchestrator flow:

```bash
curl -X POST http://localhost:8080/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"message":"analyze shipment delays","confirmed":true}'
```

6. Stop the local stack:

```bash
docker compose -f docker-compose.local.yml down
```

## Service Summary

- `backend`: orchestration, workflow planning, and evaluation/model performance.
- `control-plane`: enforcement boundary for policies, auth, and operations.
- `agent-fleet`: runtime registry and fleet lifecycle controls.
- `sandbox-agent`: constrained execution shim for task-specific agents.
- `shared`: protocol contracts and capability schemas.

## Extensibility

The platform is intentionally domain-agnostic. Domain packs can add:

- custom intents and slots
- capability manifests
- policy packs
- memory adapters
- domain-level compliance checks

## Security and Guardrails

- Policy decision points enforced by control plane.
- Delegation recursion and execution caps enforced by fleet supervisor.
- Tool execution exclusively proxied through control plane.
- End-to-end trace IDs and auditable event records.

## Evaluation & Model Performance

The evaluation engine lives inside the backend and runs directly against the orchestrator pipeline — no network hop needed.

### Built-in Suites

| Suite | What it measures |
|---|---|
| `intent` | Intent classification accuracy |
| `guardrail` | Guardrail enforcement behaviour |
| `routing` | Capability routing correctness |
| `regression` | Full combined regression |

### Endpoints

- `GET /eval/suites` — list available built-in suites.
- `POST /eval/suite/{name}` — run a built-in suite by name.
- `POST /eval/run` — run a custom suite with your own cases.

### Metrics Computed

- **Intent accuracy** — exact-match between expected and actual intents.
- **Latency** — p50/p90/p99/min/max/mean per case.
- **Token efficiency** — avg/total/min/max token counts.
- **Tool success rate** — ratio of correctly routed capabilities.
- **Guardrail compliance** — fraction of cases passing all guardrails.

### Quick Test

```bash
curl -X POST http://localhost:8080/eval/suite/regression
```

See `backend/examples/eval-run.example.json` and `shared/schemas/eval-run.schema.json` for the request contract.

## LLM Layer (Agent Brains)

- Backend maps intents to `llmProfile` routing metadata.
- Sandbox runtime loads provider/model config from environment.
- Current providers: `openai-compatible`, `azure-openai`, `anthropic`, `gemini`, `local-endpoint`, `stub`.
- Default runtime mode uses online-first failover chain before local endpoint.
- Shared profile contract example: `shared/llm/llm-routing.example.json`.

See `architecture.md` and `docs/adr` for detailed decisions.
