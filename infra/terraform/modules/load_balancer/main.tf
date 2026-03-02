resource "null_resource" "lb" {
  triggers = {
    name       = var.name
    network_id = var.network_id
  }
}

output "endpoint" {
  value = "https://${var.name}.example.internal"
}
