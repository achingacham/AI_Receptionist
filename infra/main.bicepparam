using './main.bicep'

param resourceNamePrefix = 'aireceptionist'
param location = 'centralindia'
param environment = 'prod'
param containerAppMinReplicas = 1
param containerAppMaxReplicas = 2
param containerCpuCores = '0.5'
param containerMemory = '1Gi'
param postgresqlSkuName = 'Standard_B1ms'
param postgresqlStorageGB = 32
