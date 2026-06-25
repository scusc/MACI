variable "project_name" {
  type        = string
  description = "Base name for all resources."
  default     = "maci"
}

variable "environment" {
  type        = string
  description = "Environment name (dev, staging, prod)."
  default     = "dev"
}

variable "location" {
  type        = string
  description = "Azure region to deploy resources."
  default     = "eastus" # Good default, supports all services
}

# Tags to apply to all resources for tracking/billing
locals {
  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
