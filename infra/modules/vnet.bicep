// Virtual Network module for private connectivity
param location string
param vnetName string
param tags object

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/16'
      ]
    }
    subnets: [
      {
        name: 'app-subnet'
        properties: {
          addressPrefix: '10.0.1.0/24'
          serviceEndpoints: [
            {
              service: 'Microsoft.Sql'
            }
          ]
          delegations: [
            {
              name: 'containerAppsDelegation'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        name: 'db-subnet'
        properties: {
          addressPrefix: '10.0.2.0/24'
          serviceEndpoints: [
            {
              service: 'Microsoft.Sql'
            }
          ]
        }
      }
    ]
  }
}

output vnetId string = vnet.id
output appSubnetId string = '${vnet.id}/subnets/app-subnet'
output dbSubnetId string = '${vnet.id}/subnets/db-subnet'
