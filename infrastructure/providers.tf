terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.47"
    }
  }

  # For a production setup, we would store state in an Azure Storage Account.
  # For local learning, we will keep state locally first, then migrate it.
  backend "local" {
    path = "terraform.tfstate"
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
}

provider "azuread" {
  # Provider for managing Entra ID (formerly Azure Active Directory)
  # Used for creating Service Principals and Managed Identities.
}

data "azurerm_client_config" "current" {}
