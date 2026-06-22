// Main Bicep template for AI Receptionist deployment on Azure Container Apps
// Deploys: Container Registry, Container App, PostgreSQL, Key Vault, Application Insights

metadata description = 'AI Receptionist FastAPI app on Azure Container Apps with PostgreSQL and monitoring'

// Parameters
@minLength(3)
@maxLength(24)
param resourceNamePrefix string = 'aireceptionist'

@allowed([
  'eastus'
  'westus'
  'westeurope'
  'centralindia'
  'southeastasia'
])
param location string = 'centralindia'

param environment string = 'prod'

// Environment-specific settings
param containerAppMinReplicas int = 1
param containerAppMaxReplicas int = 2
param containerCpuCores string = '0.5'
param containerMemory string = '1Gi'

// PostgreSQL settings
param postgresqlSkuName string = 'B_Standard_B1ms'
param postgresqlStorageGB int = 32

// Tags
param tags object = {
  environment: environment
  project: 'ai-receptionist'
  managed: 'bicep'
}

// Variables
var uniqueSuffix = uniqueString(resourceGroup().id)
var appName = '${resourceNamePrefix}${environment}${take(uniqueSuffix, 6)}'
var containerRegistryName = toLower(replace('${resourceNamePrefix}acr${uniqueSuffix}', '-', ''))
var containerAppName = '${appName}-app'
var containerAppEnvName = '${appName}-env'
var postgresqlServerName = '${appName}-postgres'
var keyVaultName = '${take(toLower(appName), 20)}-kv'
var appInsightsName = '${appName}-ai'
var dbUsername = 'receptionist_admin'

// Deploy Container Registry
module containerRegistry 'modules/container-registry.bicep' = {
  name: 'containerRegistry'
  params: {
    location: location
    containerRegistryName: containerRegistryName
    tags: tags
  }
}

// Deploy Key Vault
module keyVault 'modules/key-vault.bicep' = {
  name: 'keyVault'
  params: {
    location: location
    keyVaultName: keyVaultName
    tags: tags
    objectId: managedIdentity.outputs.principalId
  }
}

// Deploy managed identity
module managedIdentity 'modules/managed-identity.bicep' = {
  name: 'managedIdentity'
  params: {
    location: location
    identityName: '${appName}-identity'
    tags: tags
  }
}

// Deploy Application Insights
module appInsights 'modules/app-insights.bicep' = {
  name: 'appInsights'
  params: {
    location: location
    appInsightsName: appInsightsName
    tags: tags
  }
}

// Deploy Virtual Network for private PostgreSQL
module vnet 'modules/vnet.bicep' = {
  name: 'vnet'
  params: {
    location: location
    vnetName: '${appName}-vnet'
    tags: tags
  }
}

// Deploy PostgreSQL Database
module postgres 'modules/postgresql.bicep' = {
  name: 'postgresql'
  params: {
    location: location
    postgresqlServerName: postgresqlServerName
    postgresqlSkuName: postgresqlSkuName
    postgresqlStorageGB: postgresqlStorageGB
    administratorLogin: dbUsername
    tags: tags
  }
}

// Deploy Container App Environment
module containerAppEnv 'modules/container-app-env.bicep' = {
  name: 'containerAppEnv'
  params: {
    location: location
    containerAppEnvName: containerAppEnvName
    tags: tags
  }
}

// Deploy Container App (uses public placeholder until real image is pushed via CI/CD)
module containerApp 'modules/container-app.bicep' = {
  name: 'containerApp'
  dependsOn: [roleAssignments]
  params: {
    location: location
    containerAppName: containerAppName
    containerAppEnvId: containerAppEnv.outputs.containerAppEnvId
    containerRegistryLoginServer: containerRegistry.outputs.loginServer
    containerImage: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
    containerPort: 8000
    minReplicas: containerAppMinReplicas
    maxReplicas: containerAppMaxReplicas
    cpuCores: containerCpuCores
    memory: containerMemory
    managedIdentityId: managedIdentity.outputs.id
    keyVaultUri: keyVault.outputs.vaultUri
    postgresqlServerName: postgresqlServerName
    appInsightsInstrumentationKey: appInsights.outputs.instrumentationKey
    tags: tags
  }
}

// Assign roles
module roleAssignments 'modules/role-assignments.bicep' = {
  name: 'roleAssignments'
  params: {
    managedIdentityPrincipalId: managedIdentity.outputs.principalId
    containerRegistryId: containerRegistry.outputs.id
    keyVaultId: keyVault.outputs.id
  }
}

output containerAppName string = containerAppName
output containerAppFqdn string = containerApp.outputs.fqdn
output containerAppUrl string = containerApp.outputs.url
output containerRegistryName string = containerRegistry.outputs.name
output keyVaultName string = keyVault.outputs.name
output postgresqlServerName string = postgres.outputs.serverName
output appInsightsResourceId string = appInsights.outputs.id
output managedIdentityId string = managedIdentity.outputs.id
output resourceGroupLocation string = resourceGroup().location
output resourceGroupName string = resourceGroup().name
