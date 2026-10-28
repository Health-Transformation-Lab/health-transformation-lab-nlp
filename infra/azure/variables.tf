variable "location" {
  description = "Azure region for every resource"
  type        = string
  default     = "eastus"
}

variable "resource_group" {
  description = "Resource group that holds the telemetry resources"
  type        = string
  default     = "rg-health-transformation-lab-telemetry"
}

variable "name" {
  description = "Base name for the resources; no environment prefix or suffix (each environment is its own subscription)"
  type        = string
  default     = "health-transformation-lab-nlp"
}

variable "daily_cap_gb" {
  description = "Log Analytics daily ingestion cap in GB: 0.16 x 31 days = 4.96 GB, under the 5 GB/month free allowance"
  type        = number
  default     = 0.16
}

variable "budget_email" {
  description = "Optional email for a 1 USD monthly budget on the resource group; empty means no budget"
  type        = string
  default     = ""
}
