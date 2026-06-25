# ── AI Resource Group ───────────────────────────────────────────────────
# We separate AI resources into their own Resource Group for easier
# billing tracking, security boundary isolation, and independent lifecycles.

resource "azurerm_resource_group" "ai" {
  name     = "rg-${var.project_name}-ai-${var.environment}"
  location = var.location # We will keep it in eastus for minimal latency to AKS
  tags     = local.tags
}

# ── Azure OpenAI Service ──────────────────────────────────────────────
# 🎓 LESSON: Azure OpenAI vs OpenAI API
# Enterprise companies use Azure OpenAI because it guarantees data privacy.
# Your prompts and completions are NOT used to train Microsoft's models.

resource "azurerm_cognitive_account" "openai" {
  name                = "oai-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.ai.location
  resource_group_name = azurerm_resource_group.ai.name
  kind                = "OpenAI"

  # S0 is the standard tier for Azure OpenAI
  sku_name = "S0"

  # Disable local auth (API keys) to enforce Entra ID (RBAC) auth!
  # This means a leaked API key is impossible because they don't exist.
  local_auth_enabled = false

  tags = local.tags
}

# Deploy a specific model (e.g., GPT-4o or GPT-3.5-Turbo)
# 🎓 LESSON: Azure OpenAI constantly deprecates model versions.
# We will create the account via Terraform, but you should deploy the specific
# model version manually in Azure AI Studio to ensure you pick a supported version!
#
# resource "azurerm_cognitive_deployment" "gpt" {
#   name                 = "gpt-4o"
#   cognitive_account_id = azurerm_cognitive_account.openai.id
#
#   model {
#     format  = "OpenAI"
#     name    = "gpt-4o"
#     version = "2024-08-06"
#   }
#
#   scale {
#     type     = "Standard"
#     capacity = 10 # 10k TPM (Tokens Per Minute) limit for dev
#   }
# }

# ── Azure API Management (APIM) ───────────────────────────────────────
# 🎓 LESSON: Why use APIM for AI?
# 1. Load Balancing: If we hit TPM limits, APIM can round-robin to another region.
# 2. Token Throttling: Prevent runaway loops from bankrupting us.
# 3. Observability: APIM logs exactly who called the AI and how long it took.

resource "azurerm_api_management" "apim" {
  name                = "apim-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.ai.location
  resource_group_name = azurerm_resource_group.ai.name
  publisher_name      = "MACI"
  publisher_email     = "admin@maci.local"

  # Consumption tier is serverless, billed per execution, and deploys FAST.
  sku_name = "Consumption_0"

  # We use System Assigned identity for APIM so it can authenticate to OpenAI
  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

# ── Enterprise Security: RBAC (Zero Trust) ────────────────────────────
# 1. Grant APIM the ability to call Azure OpenAI
resource "azurerm_role_assignment" "apim_to_openai" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_api_management.apim.identity[0].principal_id
}

# 2. Grant AKS Workload Identity the ability to call APIM
# Wait, for Consumption APIM we typically authenticate via subscription keys
# or by validating JWT tokens from Entra ID via APIM policies.
# However, if we want the AKS identity to directly call OpenAI bypassing APIM
# (in case APIM is too slow to setup), we also grant the AKS identity access:
resource "azurerm_role_assignment" "aks_to_openai" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.workload.principal_id
}
