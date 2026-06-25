output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "acr_login_server" {
  value       = azurerm_container_registry.acr.login_server
  description = "The URL of the ACR (used for docker push)."
}

output "key_vault_uri" {
  value       = azurerm_key_vault.kv.vault_uri
  description = "The URI of the Key Vault (used by pods to fetch secrets)."
}
