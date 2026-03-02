resource "null_resource" "secrets" {
  triggers = {
    name = var.name
  }
}

output "secrets_ref" {
  value = "secrets://${var.name}"
}
