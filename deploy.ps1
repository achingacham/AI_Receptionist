# Deployment script for AI Receptionist to Azure (PowerShell)
# Run: .\deploy.ps1

param(
    [string]$EnvironmentFile = "infra/main.bicepparam",
    [string]$ResourceGroup = "ai-receptionist-rg",
    [string]$Location = "centralindia",
    [string]$SubscriptionId = "f658d420-86b4-4c53-aa84-ef2df0762520"
)

$TemplateFile = "infra/main.bicep"

Write-Host "🚀 Deploying AI Receptionist to Azure" -ForegroundColor Yellow
Write-Host "📦 Resource Group: $ResourceGroup" -ForegroundColor Yellow
Write-Host "📍 Location: $Location" -ForegroundColor Yellow
Write-Host "🔗 Subscription: $SubscriptionId" -ForegroundColor Yellow

# Set subscription
Write-Host "`n🔐 Setting Azure subscription..." -ForegroundColor Cyan
az account set --subscription $SubscriptionId

# Create resource group
Write-Host "`n📁 Creating resource group..." -ForegroundColor Cyan
az group create `
    --name $ResourceGroup `
    --location $Location

# Validate deployment
Write-Host "`n✓ Validating Bicep template..." -ForegroundColor Cyan
az deployment group validate `
    --resource-group $ResourceGroup `
    --template-file $TemplateFile `
    --parameters $EnvironmentFile

# What-if preview
Write-Host "`n👀 Previewing changes (what-if)..." -ForegroundColor Cyan
az deployment group what-if `
    --resource-group $ResourceGroup `
    --template-file $TemplateFile `
    --parameters $EnvironmentFile

# Deployment confirmation
$confirmation = Read-Host "`n❓ Proceed with deployment? (yes/no)"
if ($confirmation -eq "yes") {
    Write-Host "`n🌟 Deploying infrastructure..." -ForegroundColor Green
    az deployment group create `
        --resource-group $ResourceGroup `
        --template-file $TemplateFile `
        --parameters $EnvironmentFile
    
    Write-Host "`n✅ Deployment complete!" -ForegroundColor Green
} else {
    Write-Host "`n❌ Deployment cancelled" -ForegroundColor Red
}
