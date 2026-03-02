resource "null_resource" "observability" {
  triggers = {
    name = var.name
  }
}

output "telemetry_endpoint" {
  value = "otel://${var.name}"
}
