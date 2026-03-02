resource "null_resource" "network" {
  triggers = {
    name = var.name
    cidr = var.cidr
  }
}

output "network_id" {
  value = "network-${var.name}"
}
