# ── Azure Database for PostgreSQL (Flexible Server) ───────────────────
#
# 🎓 LESSON: Managed Database vs Self-Hosted
# You COULD run PostgreSQL in a Kubernetes pod. Enterprise teams NEVER do.
# Why? Because:
#   1. Azure handles backups, patching, failover, and scaling.
#   2. Data persists even if the entire K8s cluster is destroyed.
#   3. You get monitoring, threat detection, and compliance for free.
#
# 🎓 LESSON: Public Access with Firewall (Dev) vs Private Endpoint (Prod)
# For development, we allow Azure services to connect (AKS pods route
# through Azure's backbone). In production, we'd use Private Endpoints
# for full VNet isolation. We'll upgrade in a later sprint.
#

# Generate a strong random password for the DB admin
resource "random_password" "db_password" {
  length  = 32
  special = true
  override_special = "!#$%&*()-_=+[]{}|:,.<>?"
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "psql2-${var.project_name}-${var.environment}"
  resource_group_name    = azurerm_resource_group.main.name
  location               = "westus3"  # eastus is restricted for PG on this subscription
  version                = "16"
  administrator_login    = "maciadmin"
  administrator_password = random_password.db_password.result

  lifecycle {
    ignore_changes = [
      zone,
      high_availability.0.standby_availability_zone,
    ]
  }

  # 🎓 LESSON: SKU Tiers
  # Burstable (B-series): Cheap, variable CPU. Great for dev/test.
  # General Purpose: Consistent CPU. For production.
  # Memory Optimized: For heavy analytical queries.
  sku_name = "B_Standard_B1ms"  # Cheapest: 1 vCPU, 2GB RAM (~$13/month)

  storage_mb = 32768  # 32 GB

  # Dev setup: public access with Azure-only firewall rule
  # Production: Switch to VNet integration with Private Endpoints
  public_network_access_enabled = true

  tags = local.tags
}

# Firewall rule: Allow Azure services (includes AKS pods)
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Create the MACI database
resource "azurerm_postgresql_flexible_server_database" "maci" {
  name      = "maci"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# ── Store the DB password in Key Vault ────────────────────────────────
resource "azurerm_key_vault_secret" "db_password" {
  name         = "db-password"
  value        = random_password.db_password.result
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "db_connection_string" {
  name         = "db-connection-string"
  value        = "postgresql+asyncpg://maciadmin:${random_password.db_password.result}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/maci?ssl=require"
  key_vault_id = azurerm_key_vault.kv.id
}

# Also store the JWT secret in Key Vault
resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

resource "azurerm_key_vault_secret" "jwt_secret" {
  name         = "jwt-secret-key"
  value        = random_password.jwt_secret.result
  key_vault_id = azurerm_key_vault.kv.id
}
