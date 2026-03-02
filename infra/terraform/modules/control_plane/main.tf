resource "null_resource" "control_plane" {
  triggers = {
    name        = var.name
    secrets_ref = var.secrets_ref
  }
}

output "control_plane_id" {
  value = "cp-${var.name}"
}
