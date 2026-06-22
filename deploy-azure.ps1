# AI Receptionist Azure Deployment Script
# Handles Azure CLI PATH and deploys infrastructure

param(
    [string]$EnvironmentFile = "infra/main.bicepparam",
    [string]$ResourceGroup = "ai-receptionist-rg",
    [string]$Location = "centralindia",
    [string]$SubscriptionId = "f658d420-86b4-4c53-aa84-ef2df0762520"
)

# Add Azure CLI to PATH
$env:Path += ";C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin"

$TemplateFile = "infra/main.bicep"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  AI Receptionist - Azure Deployment    " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

Write-Host "`nDeployment Configuration:" -ForegroundColor Yellow
Write-Host "  Resource Group: $ResourceGroup"
Write-Host "  Location: $Location"
Write-Host "  Subscription: $SubscriptionId"
Write-Host "  Template: $TemplateFile"
Write-Host "  Parameters: $EnvironmentFile"

# Step 1: Set subscription
Write-Host "`n[1/5] Setting Azure subscription..." -ForegroundColor Cyan
az account set --subscription $SubscriptionId
if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: Subscription set successfully" -ForegroundColor Green
} else {
    Write-Host "ERROR: Failed to set subscription" -ForegroundColor Red
    exit 1
}

# Step 2: Create resource group
Write-Host "`n[2/5] Creating resource group..." -ForegroundColor Cyan
az group create `
    --name $ResourceGroup `
    --location $Location
if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: Resource group created" -ForegroundColor Green
} else {
    Write-Host "OK: Resource group already exists or created" -ForegroundColor Yellow
}

# Step 3: Validate template
Write-Host "`n[3/5] Validating Bicep template..." -ForegroundColor Cyan
az deployment group validate `
    --resource-group $ResourceGroup `
    --template-file $TemplateFile `
    --parameters $EnvironmentFile
if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: Template validation passed" -ForegroundColor Green
} else {
    Write-Host "ERROR: Template validation failed" -ForegroundColor Red
    exit 1
}

# Step 4: Preview changes (what-if)
Write-Host "`n[4/5] Previewing changes with what-if..." -ForegroundColor Cyan
az deployment group what-if `
    --resource-group $ResourceGroup `
    --template-file $TemplateFile `
    --parameters $EnvironmentFile

# Step 5: Deploy
Write-Host "`n[5/5] Ready for deployment" -ForegroundColor Cyan
$confirmation = Read-Host "Proceed with deployment? (yes/no)"
if ($confirmation -eq "yes") {
    Write-Host "`nStarting deployment..." -ForegroundColor Green
    Write-Host "This may take 10-15 minutes. Please wait...`n" -ForegroundColor Yellow
    
    az deployment group create `
        --resource-group $ResourceGroup `
        --template-file $TemplateFile `
        --parameters $EnvironmentFile
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`nSUCCESS: Deployment completed!" -ForegroundColor Green
    } else {
        Write-Host "`nERROR: Deployment failed" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "`nDeployment cancelled" -ForegroundColor Yellow
    exit 0
}
