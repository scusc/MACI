# ── Azure Service Bus ────────────────────────────────────────────────
resource "azurerm_servicebus_namespace" "main" {
  name                = "sb-${var.project_name}-${var.environment}-123"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard" # Required for topics/subscriptions

  tags = local.tags
}

resource "azurerm_key_vault_secret" "servicebus_connection_string" {
  name         = "servicebus-connection-string"
  value        = azurerm_servicebus_namespace.main.default_primary_connection_string
  key_vault_id = azurerm_key_vault.kv.id
}

# ── Azure Cache for Redis ────────────────────────────────────────────
resource "azurerm_redis_cache" "main" {
  name                = "redis-${var.project_name}-${var.environment}-123"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = 0
  family              = "C"
  sku_name            = "Basic"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"

  redis_configuration {
    maxmemory_reserved = 2
    maxmemory_delta    = 2
    maxmemory_policy   = "allkeys-lru"
  }

  tags = local.tags
}

resource "azurerm_key_vault_secret" "redis_connection_string" {
  name         = "redis-connection-string"
  value        = "redis://:${azurerm_redis_cache.main.primary_access_key}@${azurerm_redis_cache.main.hostname}:${azurerm_redis_cache.main.ssl_port}"
  key_vault_id = azurerm_key_vault.kv.id
}
