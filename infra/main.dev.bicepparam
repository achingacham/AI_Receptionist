using './main.bicep'

// AI Receptionist deployment parameters for development environment
param resourceNamePrefix = 'aireceptionist'
param location = 'centralindia'
param environment = 'dev'
param containerAppMinReplicas = 1
param containerAppMaxReplicas = 1
param containerCpuCores = '0.25'
param containerMemory = '0.5Gi'
param postgresqlSkuName = 'Standard_B1ms'
param postgresqlStorageGB = 32
