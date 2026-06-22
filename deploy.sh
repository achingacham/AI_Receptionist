#!/bin/bash
# Deployment script for AI Receptionist to Azure

set -e

# Configuration
SUBSCRIPTION_ID="f658d420-86b4-4c53-aa84-ef2df0762520"
RESOURCE_GROUP="ai-receptionist-rg"
LOCATION="centralindia"
TEMPLATE_FILE="./infra/main.bicep"
PARAM_FILE="./infra/main.bicepparam"

echo "🚀 Deploying AI Receptionist to Azure"
echo "📦 Resource Group: $RESOURCE_GROUP"
echo "📍 Location: $LOCATION"
echo "🔗 Subscription: $SUBSCRIPTION_ID"

# Set subscription
az account set --subscription $SUBSCRIPTION_ID

# Create resource group
echo "📁 Creating resource group..."
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# Validate deployment
echo "✓ Validating Bicep template..."
az deployment group validate \
  --resource-group $RESOURCE_GROUP \
  --template-file $TEMPLATE_FILE \
  --parameters $PARAM_FILE

# What-if preview
echo "👀 Previewing changes (what-if)..."
az deployment group what-if \
  --resource-group $RESOURCE_GROUP \
  --template-file $TEMPLATE_FILE \
  --parameters $PARAM_FILE

# Deploy
echo "🌟 Deploying infrastructure..."
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file $TEMPLATE_FILE \
  --parameters $PARAM_FILE

echo "✅ Deployment complete!"
