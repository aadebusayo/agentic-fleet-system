resource "null_resource" "agent_pool" {
  triggers = {
    name             = var.name
    control_plane_id = var.control_plane_id
  }
}

output "agent_pool_id" {
  value = "pool-${var.name}"
}
