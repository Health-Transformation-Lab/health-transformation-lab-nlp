output "app_insights_name" {
  value = azurerm_application_insights.appi.name
}

output "workspace_name" {
  value = azurerm_log_analytics_workspace.logs.name
}

# Read it straight into the Databricks secret (docs/telemetry.md); never print it.
output "connection_string" {
  value     = azurerm_application_insights.appi.connection_string
  sensitive = true
}
