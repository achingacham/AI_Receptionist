// PostgreSQL Database module
param location string
param postgresqlServerName string
param postgresqlSkuName string
param postgresqlStorageGB int
param administratorLogin string
param tags object

@secure()
param administratorLoginPassword string = newGuid()

resource postgresqlServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: postgresqlServerName
  location: location
  tags: tags
  sku: {
    name: postgresqlSkuName
    tier: 'Burstable'
  }
  properties: {
    version: '15'
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorLoginPassword
    storage: {
      storageSizeGB: postgresqlStorageGB
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

// Create default database
resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-12-01-preview' = {
  parent: postgresqlServer
  name: 'receptionist_db'
  properties: {
    charset: 'UTF8'
  }
}

output id string = postgresqlServer.id
output serverName string = postgresqlServer.name
output fqdn string = postgresqlServer.properties.fullyQualifiedDomainName
output databaseName string = database.name
