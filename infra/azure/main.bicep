// Pipeline telemetry on Azure (spec 014): a Log Analytics workspace with a daily ingestion cap and a
// workspace-based Application Insights resource, sized to stay inside the free allowance:
// 5 GB/month of ingestion per billing account, 90 days of Application Insights retention.
//
// Deploy (docs/telemetry.md):
//   az group create -n rg-dental-omop-telemetry -l eastus
//   az deployment group create -g rg-dental-omop-telemetry -f infra/azure/main.bicep -p budgetEmail=<you>
// Names carry no environment prefix or suffix: each environment is its own subscription or group.

@description('Region for both resources')
param location string = resourceGroup().location

@description('Base name for the resources')
param name string = 'dental-omop-nlp'

@description('Daily ingestion cap in GB. 0.16 GB/day x 31 days = 4.96 GB, under the 5 GB/month free allowance')
param dailyCapGb string = '0.16'

@description('Optional: email for a monthly cost budget of 1 USD on this resource group (empty = no budget)')
param budgetEmail string = ''

@description('First day of the current month, for the budget period')
param budgetStartDate string = utcNow('yyyy-MM-01')

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${name}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30                          // free for general tables; App Insights tables keep 90
    workspaceCapping: { dailyQuotaGb: json(dailyCapGb) }
    features: { enableLogAccessUsingOnlyResourcePermissions: true }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${name}-appi'
  location: location
  kind: 'other'
  properties: {
    Application_Type: 'other'
    WorkspaceResourceId: workspace.id
    IngestionMode: 'LogAnalytics'
    RetentionInDays: 90
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

resource budget 'Microsoft.Consumption/budgets@2023-11-01' = if (!empty(budgetEmail)) {
  name: '${name}-budget'
  properties: {
    category: 'Cost'
    amount: 1
    timeGrain: 'Monthly'
    timePeriod: { startDate: budgetStartDate }
    notifications: {
      anySpend: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 1                             // percent of 1 USD: any charge at all
        contactEmails: [ budgetEmail ]
        thresholdType: 'Actual'
      }
    }
  }
}

// The connection string is not an output (outputs are stored in the deployment history);
// read it with: az monitor app-insights component show -g <group> -a <name>-appi --query connectionString
output appInsightsName string = appInsights.name
output workspaceName string = workspace.name
