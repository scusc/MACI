# ── Virtual Network (VNet) ────────────────────────────────────────────
#
# 🎓 LESSON: What is a VNet?
# A VNet is your private network in Azure — like having your own
# office building. Resources inside the VNet can talk to each other
# on private IP addresses (10.x.x.x), completely invisible to the
# public internet.
#
# We create separate "subnets" (floors in the building):
#   - AKS subnet: Where our Kubernetes pods live
#   - DB subnet:  Where our PostgreSQL database lives
#
# By putting the DB in a separate subnet, we can apply Network Security
# Group (NSG) rules that say "only traffic from the AKS subnet can
# reach the database." This is Zero Trust Networking.
#

resource "azurerm_virtual_network" "main" {
  name                = "vnet-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.0.0.0/16"] # 65,536 IP addresses

  tags = local.tags
}

# Subnet for AKS pods and nodes
resource "azurerm_subnet" "aks" {
  name                 = "snet-aks"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"] # 256 addresses — enough for learning
}

# Subnet for Azure PostgreSQL (delegated)
# 🎓 LESSON: "Delegation" means we're telling Azure that ONLY
# PostgreSQL Flexible Servers are allowed to use this subnet.
# This is required by Azure for VNet-integrated databases.
resource "azurerm_subnet" "db" {
  name                 = "snet-db"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]

  delegation {
    name = "postgresql-delegation"

    service_delegation {
      name = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
      ]
    }
  }
}

# Private DNS Zone for PostgreSQL
# 🎓 LESSON: When we put PostgreSQL behind a Private Endpoint / VNet,
# it no longer has a public DNS name. We need a Private DNS Zone so
# our AKS pods can resolve "maci-db.postgres.database.azure.com" to
# the PRIVATE IP (10.0.2.x) instead of a public IP.
resource "azurerm_private_dns_zone" "postgres" {
  name                = "${var.project_name}-${var.environment}.private.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.main.name

  tags = local.tags
}

# Link the DNS zone to our VNet so pods can resolve the DB hostname
resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "postgres-vnet-link"
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  virtual_network_id    = azurerm_virtual_network.main.id
  resource_group_name   = azurerm_resource_group.main.name
}
