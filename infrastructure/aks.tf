# ── Azure Kubernetes Service (AKS) ────────────────────────────────────
#
# 🎓 LESSON: AKS Architecture
# AKS has two parts:
#   1. Control Plane (FREE) — Microsoft manages this. It runs the
#      Kubernetes API server, scheduler, etcd, etc. You never touch it.
#   2. Node Pool (YOU PAY) — These are the VMs where your pods actually
#      run. We use Standard_B2s (2 vCPU, 4GB RAM, ~$30/month).
#
# 🎓 LESSON: Workload Identity
# Traditional approach: Put DB password in an env var → BAD.
# Enterprise approach:  Our K8s ServiceAccount is federated with an
#   Azure Managed Identity. When a pod starts, it gets a token from
#   Azure AD and uses it to read secrets from Key Vault. No password
#   ever exists in our YAML or container image.
#
# To enable this, we set:
#   - oidc_issuer_enabled = true    (AKS publishes an OIDC discovery doc)
#   - workload_identity_enabled = true (enables the mutating webhook)
#

resource "azurerm_kubernetes_cluster" "aks" {
  name                = "aks-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = "${var.project_name}-${var.environment}"

  # Free tier — no SLA, but $0 for the control plane
  sku_tier = "Free"

  # Enable Workload Identity (the enterprise secret management pattern)
  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  # System-assigned identity for the AKS cluster itself
  # This is different from Workload Identity — this identity is used
  # by the AKS control plane to manage Azure resources (like pulling
  # images from ACR, managing load balancers, etc.)
  identity {
    type = "SystemAssigned"
  }

  # Default node pool — the VMs where our pods run
  default_node_pool {
    name                = "system"
    node_count          = 1           # Single node for learning (scale up later)
    vm_size             = "Standard_D2als_v7"  # 2 vCPU, 4GB RAM — cheapest allowed in this subscription
    vnet_subnet_id      = azurerm_subnet.aks.id
    os_disk_size_gb     = 30

    # 🎓 LESSON: Node labels let you target specific pods to specific nodes.
    # In production, you'd have "system" nodes for K8s overhead and
    # "workload" nodes for your apps.
    node_labels = {
      "role" = "system"
    }
  }

  # Network profile — use Azure CNI for VNet integration
  # 🎓 LESSON: CNI vs Kubenet
  #   - Kubenet: Pods get IPs from a virtual network (overlay). Simple but limited.
  #   - Azure CNI: Pods get REAL IPs from the VNet subnet. This means pods
  #     can directly communicate with VNet-integrated services like PostgreSQL.
  #     Enterprise teams always use CNI.
  network_profile {
    network_plugin = "azure"
    service_cidr   = "10.1.0.0/16"    # Internal K8s service IPs
    dns_service_ip = "10.1.0.10"       # K8s internal DNS
  }

  tags = local.tags
}

# ── Grant AKS permission to pull images from our ACR ──────────────────
# 🎓 LESSON: AcrPull Role
# Without this, AKS can't download Docker images from our private ACR.
# We grant the MINIMUM permission needed: "AcrPull" (read-only).
# This is Principle of Least Privilege in action.
resource "azurerm_role_assignment" "aks_acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.acr.id
  skip_service_principal_aad_check = true
}
