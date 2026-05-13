// Container App module for FastAPI application
param location string
param containerAppName string
param containerAppEnvId string
param containerRegistryLoginServer string
param containerImage string
param containerPort int
param minReplicas int
param maxReplicas int
param cpuCores string
param memory string
param managedIdentityId string
param keyVaultUri string
param postgresqlServerName string
@secure()
param appInsightsInstrumentationKey string
param tags object

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppEnvId
    configuration: {
      ingress: {
        external: true
        targetPort: containerPort
        transport: 'auto'
      }
      dapr: {
        enabled: false
      }
      registries: [
        {
          server: containerRegistryLoginServer
          identity: managedIdentityId
        }
      ]
      secrets: [
        {
          name: 'appinsights-key'
          value: appInsightsInstrumentationKey
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'receptionist'
          image: containerImage
          resources: {
            cpu: json(cpuCores)
            memory: memory
          }
          env: [
            {
              name: 'PORT'
              value: string(containerPort)
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsightsInstrumentationKey
            }
            {
              name: 'KEYVAULT_URI'
              value: keyVaultUri
            }
            {
              name: 'DATABASE_URL'
              value: 'postgresql://user:pass@${postgresqlServerName}.postgres.database.azure.com/receptionist_db'
            }
          ]
          probes: [
            {
              type: 'Startup'
              httpGet: {
                path: '/health'
                port: containerPort
              }
              initialDelaySeconds: 10
              periodSeconds: 5
              failureThreshold: 3
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: containerPort
              }
              initialDelaySeconds: 20
              periodSeconds: 30
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: containerPort
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
      terminationGracePeriodSeconds: 30
    }
  }
}

output fqdn string = containerApp.properties.configuration.ingress.fqdn
output url string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output id string = containerApp.id
