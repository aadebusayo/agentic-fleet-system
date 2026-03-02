terraform {
  required_version = ">= 1.8.0"
}

module "network" {
  source = "../../modules/network"
  name   = "agent-platform-dev"
  cidr   = "10.40.0.0/16"
}

module "secrets" {
  source = "../../modules/secrets"
  name   = "agent-platform-dev"
}

module "observability" {
  source = "../../modules/observability"
  name   = "agent-platform-dev"
}

module "control_plane" {
  source      = "../../modules/control_plane"
  name        = "agent-platform-dev"
  secrets_ref = module.secrets.secrets_ref
}

module "agent_pool" {
  source           = "../../modules/agent_pool"
  name             = "agent-platform-dev"
  control_plane_id = module.control_plane.control_plane_id
}

module "load_balancer" {
  source     = "../../modules/load_balancer"
  name       = "agent-platform-dev"
  network_id = module.network.network_id
}

output "ingress_endpoint" {
  value = module.load_balancer.endpoint
}

output "telemetry_endpoint" {
  value = module.observability.telemetry_endpoint
}
