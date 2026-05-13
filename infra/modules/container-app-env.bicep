// Container App Environment module
param location string
param containerAppEnvName string
param tags object

resource containerAppEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppEnvName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
  }
}

output containerAppEnvId string = containerAppEnv.id
output containerAppEnvName string = containerAppEnv.name
