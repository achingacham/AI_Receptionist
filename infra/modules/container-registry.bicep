// Container Registry module
param location string
param containerRegistryName string
param tags object

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: containerRegistryName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false // Disable admin for security
    publicNetworkAccess: 'Enabled'
    networkRuleBypassOptions: 'AzureServices'
    anonymousPullEnabled: false // Security best practice: disable anonymous pull
  }
}

output id string = containerRegistry.id
output name string = containerRegistry.name
output loginServer string = containerRegistry.properties.loginServer
