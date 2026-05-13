// Key Vault module for secrets management
param location string
param keyVaultName string
param tags object
param objectId string

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: objectId
        permissions: {
          secrets: [
            'get'
            'list'
          ]
          certificates: [
            'get'
            'list'
          ]
        }
      }
    ]
    enabledForDeployment: false
    enabledForTemplateDeployment: false
    enabledForDiskEncryption: false
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: true // Enable purge protection for production
    publicNetworkAccess: 'Enabled'
  }
}

output id string = keyVault.id
output name string = keyVault.name
output vaultUri string = keyVault.properties.vaultUri
