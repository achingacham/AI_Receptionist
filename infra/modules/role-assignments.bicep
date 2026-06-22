// Role Assignments module for managed identity permissions
param managedIdentityPrincipalId string
param containerRegistryId string
param keyVaultId string

// Role IDs (built-in Azure roles)
var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6' // Key Vault Secrets User
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d' // AcrPull built-in role

// Key Vault Secrets User role assignment
resource keyVaultSecretsUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVaultId, managedIdentityPrincipalId, keyVaultSecretsUserRoleId)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: '/subscriptions/${subscription().subscriptionId}/providers/Microsoft.Authorization/roleDefinitions/${keyVaultSecretsUserRoleId}'
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// ACR Pull role assignment for container registry access
resource acrPullAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistryId, managedIdentityPrincipalId, acrPullRoleId)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: '/subscriptions/${subscription().subscriptionId}/providers/Microsoft.Authorization/roleDefinitions/${acrPullRoleId}'
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output keyVaultAssignmentId string = keyVaultSecretsUserAssignment.id
output acrPullAssignmentId string = acrPullAssignment.id
