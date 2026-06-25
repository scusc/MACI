# ── 1. Resource Group ────────────────────────────────────────────────
# All resources must live inside a Resource Group.
resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project_name}-${var.environment}-${var.location}"
  location = var.location
  tags     = local.tags
}

# ── 2. Azure Container Registry (ACR) ────────────────────────────────
# Private registry to store our Docker images (auth-service, trip-service).
# Needs a globally unique name (alphanumeric only).
resource "azurerm_container_registry" "acr" {
  name                = "acr${var.project_name}${var.environment}123" # Added 123 for uniqueness safety
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic" # Basic is cheapest for learning
  admin_enabled       = true    # Enables docker login with password (useful for local dev)

  tags = local.tags
}

# ── 3. Azure Key Vault (AKV) ─────────────────────────────────────────
# Secure store for our DB passwords, LLM keys, etc.
resource "azurerm_key_vault" "kv" {
  name                        = "kv-${var.project_name}-${var.environment}-123"
  location                    = azurerm_resource_group.main.location
  resource_group_name         = azurerm_resource_group.main.name
  enabled_for_disk_encryption = true
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false

  sku_name = "standard"

  # Access Policy to allow the user running Terraform to manage secrets
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    key_permissions = ["Get", "List", "Create", "Delete", "Recover", "Backup", "Restore", "Purge"]
    secret_permissions = ["Get", "List", "Set", "Delete", "Recover", "Backup", "Restore", "Purge"]
  }

  tags = local.tags
}
