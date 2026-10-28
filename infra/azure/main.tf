# Pipeline telemetry on Azure (spec 014): a Log Analytics workspace with a daily ingestion cap and a
# workspace-based Application Insights resource, sized to stay inside the free allowance
# (5 GB/month of ingestion per billing account; 90 days of Application Insights retention included).
# Setup: docs/telemetry.md.

resource "azurerm_resource_group" "telemetry" {
  name     = var.resource_group
  location = var.location
}

resource "azurerm_log_analytics_workspace" "logs" {
  name                = "${var.name}-logs"
  location            = azurerm_resource_group.telemetry.location
  resource_group_name = azurerm_resource_group.telemetry.name
  sku                 = "PerGB2018"
  retention_in_days   = 30 # free for general tables; Application Insights tables keep 90
  daily_quota_gb      = var.daily_cap_gb
}

resource "azurerm_application_insights" "appi" {
  name                = "${var.name}-appi"
  location            = azurerm_resource_group.telemetry.location
  resource_group_name = azurerm_resource_group.telemetry.name
  workspace_id        = azurerm_log_analytics_workspace.logs.id
  application_type    = "other"
  retention_in_days   = 90
}

resource "azurerm_consumption_budget_resource_group" "budget" {
  count             = var.budget_email == "" ? 0 : 1
  name              = "${var.name}-budget"
  resource_group_id = azurerm_resource_group.telemetry.id
  amount            = 1
  time_grain        = "Monthly"

  time_period {
    start_date = formatdate("YYYY-MM-01'T'00:00:00Z", timestamp())
  }

  notification {
    enabled        = true
    threshold      = 1 # percent of 1 USD: any actual charge
    operator       = "GreaterThan"
    threshold_type = "Actual"
    contact_emails = [var.budget_email]
  }

  lifecycle {
    ignore_changes = [time_period] # the start date is set once, at creation
  }
}
