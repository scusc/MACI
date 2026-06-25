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

# ── Sprint 3 Outputs ─────────────────────────────────────────────────

output "aks_cluster_name" {
  value       = azurerm_kubernetes_cluster.aks.name
  description = "Name of the AKS cluster (used with kubectl)."
}

output "aks_oidc_issuer_url" {
  value       = azurerm_kubernetes_cluster.aks.oidc_issuer_url
  description = "OIDC issuer URL for Workload Identity federation."
}

output "postgres_fqdn" {
  value       = azurerm_postgresql_flexible_server.main.fqdn
  description = "Fully qualified domain name of the PostgreSQL server."
  sensitive   = true
}

output "workload_identity_client_id" {
  value       = azurerm_user_assigned_identity.workload.client_id
  description = "Client ID of the Managed Identity (used in K8s ServiceAccount annotation)."
}

output "vnet_name" {
  value = azurerm_virtual_network.main.name
}
