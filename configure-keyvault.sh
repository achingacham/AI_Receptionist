#!/bin/bash
# Post-deployment configuration for AI Receptionist
# This script configures Azure Key Vault with all required secrets

set -e

RESOURCE_GROUP="ai-receptionist-rg"
KEY_VAULT_NAME=$(az deployment group show -g $RESOURCE_GROUP --name containerRegistry -o json | jq -r '.properties.outputs.keyVaultName.value')

echo "🔑 Configuring Azure Key Vault: $KEY_VAULT_NAME"

# Read original .env file
echo "📖 Reading .env file..."

# Database password
read -sp "Enter PostgreSQL admin password: " DB_PASSWORD
echo

# Set secrets in Key Vault
echo "🔐 Setting secrets in Key Vault..."

az keyvault secret set --name "GROQ-API-KEY" --vault-name $KEY_VAULT_NAME --value $(grep "^GROQ_API_KEY=" .env | cut -d= -f2-)
az keyvault secret set --name "DATABASE-PASSWORD" --vault-name $KEY_VAULT_NAME --value "$DB_PASSWORD"
az keyvault secret set --name "SARVAM-API-KEY" --vault-name $KEY_VAULT_NAME --value $(grep "^SARVAM_API_KEY=" .env | cut -d= -f2-)
az keyvault secret set --name "TWILIO-ACCOUNT-SID" --vault-name $KEY_VAULT_NAME --value $(grep "^TWILIO_ACCOUNT_SID=" .env | cut -d= -f2-)
az keyvault secret set --name "TWILIO-AUTH-TOKEN" --vault-name $KEY_VAULT_NAME --value $(grep "^TWILIO_AUTH_TOKEN=" .env | cut -d= -f2-)
az keyvault secret set --name "CALCOM-API-KEY" --vault-name $KEY_VAULT_NAME --value $(grep "^CALCOM_API_KEY=" .env | cut -d= -f2-)

echo "✅ Key Vault configuration complete!"
