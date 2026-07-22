#!/usr/bin/env bash
# Azure utilization check for AI Receptionist
# Resources: Container App, ACR, PostgreSQL, Key Vault, App Insights
# Usage: bash azure-utilization.sh [--hours N]

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
SUBSCRIPTION="f658d420-86b4-4c53-aa84-ef2df0762520"
RESOURCE_GROUP="ai-receptionist-rg"
LOCATION="centralindia"
HOURS="${2:-1}"           # default: last 1 hour
START_TIME=$(date -u -d "-${HOURS} hours" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
           || date -u -v-"${HOURS}H" +"%Y-%m-%dT%H:%M:%SZ")  # macOS fallback
END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ── Helpers ───────────────────────────────────────────────────────────────────
bold='\033[1m'; cyan='\033[0;36m'; green='\033[0;32m'; yellow='\033[1;33m'
red='\033[0;31m'; reset='\033[0m'

section() { echo -e "\n${cyan}${bold}══════════════════════════════════════${reset}"; \
            echo -e "${cyan}${bold}  $1${reset}"; \
            echo -e "${cyan}${bold}══════════════════════════════════════${reset}"; }
info()    { echo -e "  ${green}▸${reset} $1"; }
warn()    { echo -e "  ${yellow}⚠${reset}  $1"; }

# ── Login check ───────────────────────────────────────────────────────────────
section "Azure Login"
CURRENT_SUB=$(az account show --query id -o tsv 2>/dev/null || echo "")
if [[ "$CURRENT_SUB" != "$SUBSCRIPTION" ]]; then
  warn "Not logged in or wrong subscription. Switching..."
  az account set --subscription "$SUBSCRIPTION"
fi

SUB_NAME=$(az account show --query name -o tsv)
SUB_ID=$(az account show --query id -o tsv)
SUB_TENANT=$(az account show --query tenantId -o tsv)
SUB_USER=$(az account show --query user.name -o tsv)
SUB_STATE=$(az account show --query state -o tsv)

echo ""
echo -e "  ${bold}Subscription Details${reset}"
echo -e "  ┌─────────────────────────────────────────────────────────"
echo -e "  │  ${bold}Name        :${reset} ${SUB_NAME}"
echo -e "  │  ${bold}ID          :${reset} ${SUB_ID}"
echo -e "  │  ${bold}Tenant ID   :${reset} ${SUB_TENANT}"
echo -e "  │  ${bold}Logged in as:${reset} ${SUB_USER}"
echo -e "  │  ${bold}State       :${reset} ${green}${SUB_STATE}${reset}"
echo -e "  │  ${bold}Resource Grp:${reset} ${RESOURCE_GROUP}"
echo -e "  │  ${bold}Location    :${reset} ${LOCATION}"
echo -e "  │  ${bold}Time Window :${reset} last ${HOURS}h  (${START_TIME} → ${END_TIME})"
echo -e "  └─────────────────────────────────────────────────────────"

# ── Discover dynamic resource names ───────────────────────────────────────────
section "Discovered Resources"
CONTAINER_APP=$(az containerapp list -g "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || echo "")
CONTAINER_APP_ENV=$(az containerapp env list -g "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || echo "")
POSTGRES_SERVER=$(az postgres flexible-server list -g "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || echo "")
KEY_VAULT=$(az keyvault list -g "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || echo "")
APP_INSIGHTS=$(az monitor app-insights component list -g "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || echo "")
ACR=$(az acr list -g "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || echo "")

echo ""
echo -e "  ${bold}Resource Inventory${reset}"
echo -e "  ┌─────────────────────────────────────────────────────────"
echo -e "  │  ${bold}Container App    :${reset} ${CONTAINER_APP:-${red}<not found>${reset}}"
echo -e "  │  ${bold}App Environment  :${reset} ${CONTAINER_APP_ENV:-${red}<not found>${reset}}"
echo -e "  │  ${bold}PostgreSQL Server:${reset} ${POSTGRES_SERVER:-${red}<not found>${reset}}"
echo -e "  │  ${bold}Key Vault        :${reset} ${KEY_VAULT:-${red}<not found>${reset}}"
echo -e "  │  ${bold}App Insights     :${reset} ${APP_INSIGHTS:-${red}<not found>${reset}}"
echo -e "  │  ${bold}Container Reg.   :${reset} ${ACR:-${red}<not found>${reset}}"
echo -e "  └─────────────────────────────────────────────────────────"

# ── Container App ─────────────────────────────────────────────────────────────
if [[ -n "$CONTAINER_APP" ]]; then
  section "Container App — $CONTAINER_APP"

  # Status & replicas
  az containerapp show -n "$CONTAINER_APP" -g "$RESOURCE_GROUP" \
    --query "{status:properties.runningStatus, \
              replicas:properties.template.scale.minReplicas, \
              maxReplicas:properties.template.scale.maxReplicas, \
              cpu:properties.template.containers[0].resources.cpu, \
              memory:properties.template.containers[0].resources.memory, \
              image:properties.template.containers[0].image}" \
    -o table

  # Live replica count
  info "Current replica count:"
  az containerapp replica list -n "$CONTAINER_APP" -g "$RESOURCE_GROUP" \
    --query "length(@)" -o tsv 2>/dev/null || echo "    N/A"

  # CPU & Memory metrics
  APP_ID=$(az containerapp show -n "$CONTAINER_APP" -g "$RESOURCE_GROUP" --query id -o tsv)
  info "CPU usage (avg %) — last ${HOURS}h:"
  az monitor metrics list --resource "$APP_ID" \
    --metric "CpuUsage" \
    --start-time "$START_TIME" --end-time "$END_TIME" \
    --interval PT5M \
    --aggregation Average \
    --query "value[0].timeseries[0].data[-5:].{time:timeStamp, avg:average}" \
    -o table 2>/dev/null || warn "CPU metrics unavailable"

  info "Memory usage (avg bytes) — last ${HOURS}h:"
  az monitor metrics list --resource "$APP_ID" \
    --metric "MemoryWorkingSetBytes" \
    --start-time "$START_TIME" --end-time "$END_TIME" \
    --interval PT5M \
    --aggregation Average \
    --query "value[0].timeseries[0].data[-5:].{time:timeStamp, avg:average}" \
    -o table 2>/dev/null || warn "Memory metrics unavailable"

  info "HTTP requests (count) — last ${HOURS}h:"
  az monitor metrics list --resource "$APP_ID" \
    --metric "Requests" \
    --start-time "$START_TIME" --end-time "$END_TIME" \
    --interval PT5M \
    --aggregation Total \
    --query "value[0].timeseries[0].data[-5:].{time:timeStamp, total:total}" \
    -o table 2>/dev/null || warn "Request metrics unavailable"
fi

# ── PostgreSQL ─────────────────────────────────────────────────────────────────
if [[ -n "$POSTGRES_SERVER" ]]; then
  section "PostgreSQL Flexible Server — $POSTGRES_SERVER"

  az postgres flexible-server show -n "$POSTGRES_SERVER" -g "$RESOURCE_GROUP" \
    --query "{state:state, sku:sku.name, tier:sku.tier, \
              storageMB:storage.storageSizeGb, version:version, \
              backup:backup.backupRetentionDays}" \
    -o table

  PG_ID=$(az postgres flexible-server show -n "$POSTGRES_SERVER" -g "$RESOURCE_GROUP" --query id -o tsv)

  info "CPU percent — last ${HOURS}h:"
  az monitor metrics list --resource "$PG_ID" \
    --metric "cpu_percent" \
    --start-time "$START_TIME" --end-time "$END_TIME" \
    --interval PT5M --aggregation Average \
    --query "value[0].timeseries[0].data[-5:].{time:timeStamp, cpu:average}" \
    -o table 2>/dev/null || warn "CPU metrics unavailable"

  info "Active connections — last ${HOURS}h:"
  az monitor metrics list --resource "$PG_ID" \
    --metric "active_connections" \
    --start-time "$START_TIME" --end-time "$END_TIME" \
    --interval PT5M --aggregation Average \
    --query "value[0].timeseries[0].data[-5:].{time:timeStamp, connections:average}" \
    -o table 2>/dev/null || warn "Connection metrics unavailable"

  info "Storage used (bytes):"
  az monitor metrics list --resource "$PG_ID" \
    --metric "storage_used" \
    --start-time "$START_TIME" --end-time "$END_TIME" \
    --interval PT1H --aggregation Average \
    --query "value[0].timeseries[0].data[-1:].{time:timeStamp, usedBytes:average}" \
    -o table 2>/dev/null || warn "Storage metrics unavailable"
fi

# ── Container Registry ────────────────────────────────────────────────────────
if [[ -n "$ACR" ]]; then
  section "Container Registry — $ACR"

  az acr show -n "$ACR" --query "{sku:sku.name, loginServer:loginServer, \
    adminEnabled:adminUserEnabled, storageUsedGB:storageUsedBytes}" \
    -o table 2>/dev/null || az acr show -n "$ACR" --query \
    "{sku:sku.name, loginServer:loginServer, adminEnabled:adminUserEnabled}" -o table

  info "Recent pushes (last 5):"
  az acr repository list -n "$ACR" -o tsv 2>/dev/null | while read -r repo; do
    echo "    Repo: $repo"
    az acr repository show-tags -n "$ACR" --repository "$repo" \
      --orderby time_desc --top 3 -o tsv 2>/dev/null | sed 's/^/      tag: /'
  done || warn "Could not list repositories"
fi

# ── Key Vault ─────────────────────────────────────────────────────────────────
if [[ -n "$KEY_VAULT" ]]; then
  section "Key Vault — $KEY_VAULT"

  az keyvault show -n "$KEY_VAULT" \
    --query "{sku:properties.sku.name, enabled:properties.enabledForDeployment, \
              softDelete:properties.enableSoftDelete}" \
    -o table

  info "Secret count:"
  az keyvault secret list --vault-name "$KEY_VAULT" --query "length(@)" -o tsv 2>/dev/null \
    || warn "No access to list secrets"
fi

# ── Application Insights ──────────────────────────────────────────────────────
if [[ -n "$APP_INSIGHTS" ]]; then
  section "Application Insights — $APP_INSIGHTS"

  AI_ID=$(az monitor app-insights component show -a "$APP_INSIGHTS" -g "$RESOURCE_GROUP" \
    --query id -o tsv 2>/dev/null || echo "")

  if [[ -n "$AI_ID" ]]; then
    info "Failed requests — last ${HOURS}h:"
    az monitor metrics list --resource "$AI_ID" \
      --metric "requests/failed" \
      --start-time "$START_TIME" --end-time "$END_TIME" \
      --interval PT5M --aggregation Count \
      --query "value[0].timeseries[0].data[-5:].{time:timeStamp, failed:count}" \
      -o table 2>/dev/null || warn "Failed-request metrics unavailable"

    info "Avg server response time (ms):"
    az monitor metrics list --resource "$AI_ID" \
      --metric "requests/duration" \
      --start-time "$START_TIME" --end-time "$END_TIME" \
      --interval PT5M --aggregation Average \
      --query "value[0].timeseries[0].data[-5:].{time:timeStamp, avgMs:average}" \
      -o table 2>/dev/null || warn "Response time metrics unavailable"
  fi
fi

# ── Cost estimate (last 30 days) ──────────────────────────────────────────────
section "Cost — Last 30 Days"
az consumption usage list \
  --start-date "$(date -u -d '-30 days' +%Y-%m-%d 2>/dev/null || date -u -v-30d +%Y-%m-%d)" \
  --end-date "$(date -u +%Y-%m-%d)" \
  --query "sort_by([?resourceGroup=='${RESOURCE_GROUP}'], &pretaxCost)[-10:].{service:instanceName, cost:pretaxCost, currency:currency}" \
  -o table 2>/dev/null || warn "Cost data unavailable (may need 'Microsoft.CostManagement' access)"

section "Done"
echo -e "  Run ${yellow}bash azure-utilization.sh --hours 24${reset} for a 24-hour window."
echo ""
echo -e "  ${bold}Stop/Start the app:${reset}"
echo -e "  ${yellow}# Stop${reset}"
echo -e "  REVISION=\$(az containerapp revision list -n \"\$CONTAINER_APP\" -g \"\$RESOURCE_GROUP\" --query \"[?properties.active==\\\`true\\\`].name\" -o tsv)"
echo -e "  az containerapp revision deactivate -n \"\$CONTAINER_APP\" -g \"\$RESOURCE_GROUP\" --revision \"\$REVISION\""
echo -e "  ${yellow}# Start${reset}"
echo -e "  az containerapp revision activate -n \"\$CONTAINER_APP\" -g \"\$RESOURCE_GROUP\" --revision \"\$REVISION\""
echo ""
