# ── Managed Identity & Workload Identity ──────────────────────────────
#
# 🎓 LESSON: The Identity Chain (How Pods Get Secrets)
#
# Step 1: We create a User-Assigned Managed Identity in Azure.
# Step 2: We give that identity permission to READ secrets from Key Vault.
# Step 3: We create a "Federated Identity Credential" that says:
#          "Any Kubernetes ServiceAccount named 'maci-workload-sa' in
#           namespace 'maci' is allowed to assume this Azure identity."
# Step 4: In our K8s deployment YAML, our pods use that ServiceAccount.
# Step 5: When the pod starts, the Workload Identity webhook injects
#          Azure tokens into the pod. Our code uses these tokens to
#          read the DB password from Key Vault.
#
# Result: The password NEVER exists as text in any file.
#

# The Managed Identity that our pods will assume
resource "azurerm_user_assigned_identity" "workload" {
  name                = "id-${var.project_name}-workload-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = local.tags
}

# Grant the Managed Identity permission to read Key Vault secrets
# 🎓 LESSON: "Key Vault Secrets User" is a built-in Azure RBAC role.
# It allows GET and LIST on secrets only. It cannot SET/DELETE.
# This is Principle of Least Privilege — our pods can read secrets
# but cannot modify or delete them.
resource "azurerm_key_vault_access_policy" "workload" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_user_assigned_identity.workload.principal_id

  secret_permissions = ["Get", "List"]
}

# Federated Identity Credential — the bridge between K8s and Azure
# 🎓 LESSON: This is the magic glue. It tells Azure:
# "When a token comes from AKS's OIDC issuer, signed for the subject
#  'system:serviceaccount:maci:maci-workload-sa', trust it as this
#  Managed Identity."
resource "azurerm_federated_identity_credential" "workload" {
  name                = "fed-${var.project_name}-workload"
  resource_group_name = azurerm_resource_group.main.name
  parent_id           = azurerm_user_assigned_identity.workload.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.aks.oidc_issuer_url
  subject             = "system:serviceaccount:maci:maci-workload-sa"
  # Format: system:serviceaccount:<namespace>:<service-account-name>
}
