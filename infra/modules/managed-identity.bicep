// Managed Identity module for secure authentication
param location string
param identityName string
param tags object

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
  tags: tags
}

output id string = managedIdentity.id
output principalId string = managedIdentity.properties.principalId
