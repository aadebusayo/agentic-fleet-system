# Terraform

Cloud-agnostic infrastructure modules for the agent platform.

## Modules

- `network`: virtual network and subnet placeholders
- `load_balancer`: edge ingress abstraction
- `secrets`: secret store abstraction
- `observability`: logs/metrics/tracing sink abstraction
- `control_plane`: control-plane compute/runtime abstraction
- `agent_pool`: autoscaled agent runtime pool abstraction

## Environments

- `environments/dev`: composed stack for local/dev deployment
