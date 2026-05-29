#!/usr/bin/env python3
"""
Azure Deployment Agent for AI Receptionist.

Orchestrates the full deployment pipeline:
  1. Pre-flight checks (Azure CLI, Docker, auth)
  2. Bicep infrastructure deployment
  3. Docker image build + push to ACR
  4. Key Vault secret configuration
  5. Container App update (new image + env vars)
  6. Health verification

Usage:
    python deploy_agent.py [--skip-infra] [--skip-build] [--skip-secrets]
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ─── Project constants ────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent
ENV_FILE = PROJECT_ROOT / ".env"
BICEP_MAIN = PROJECT_ROOT / "infra" / "main.bicep"
BICEP_PARAMS = PROJECT_ROOT / "infra" / "main.bicepparam"

SUBSCRIPTION_ID = "7fe7cb77-5aaf-4887-8a6c-91698815e2a6"
RESOURCE_GROUP = "ai-receptionist-rg"
LOCATION = "centralindia"
DEPLOYMENT_NAME = "aireceptionist-deployment"
IMAGE_NAME = "ai-receptionist"

# Mapping from .env key → Azure Key Vault secret name
KEYVAULT_SECRETS_MAP = {
    "GROQ_API_KEY": "GROQ-API-KEY",
    "SARVAM_API_KEY": "SARVAM-API-KEY",
    "TWILIO_ACCOUNT_SID": "TWILIO-ACCOUNT-SID",
    "TWILIO_AUTH_TOKEN": "TWILIO-AUTH-TOKEN",
    "EXOTEL_SID": "EXOTEL-SID",
    "EXOTEL_TOKEN": "EXOTEL-TOKEN",
    "CALCOM_API_KEY": "CALCOM-API-KEY",
}

# Non-sensitive config keys passed as direct Container App env vars
CONTAINER_ENV_KEYS = [
    "GROQ_MODEL",
    "GROQ_API_URL",
    "BUSINESS_NAME",
    "BUSINESS_HOURS",
    "BUSINESS_PHONE",
    "BUSINESS_EMAIL",
    "BUSINESS_ADDRESS",
    "RECEPTIONIST_NAME",
    "CALCOM_USERNAME",
    "CALCOM_EVENT_TYPE_ID",
    "CALCOM_TIMEZONE",
    "CALCOM_FALLBACK_EMAIL",
    "VOICE_PROVIDER",
    "TWILIO_PHONE_NUMBER",
    "PLIVO_PHONE_NUMBER",
    "EXOTEL_PHONE_NUMBER",
    "EXOTEL_SUBDOMAIN",
]


# ─── Utilities ────────────────────────────────────────────────────────────────

def header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def warn(msg: str) -> None:
    print(f"  ! {msg}")


def fail(msg: str) -> None:
    print(f"\n[FATAL] {msg}")
    sys.exit(1)


def run(args: list[str], *, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    """Run a command, print it, and exit on failure when check=True."""
    display = " ".join(str(a) for a in args)
    print(f"    $ {display}")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    # On Windows, az/acr/containerapp are .cmd files that require shell=True.
    # subprocess.list2cmdline quotes args safely for cmd.exe.
    if sys.platform == "win32":
        cmd = subprocess.list2cmdline(args)
        result = subprocess.run(cmd, capture_output=capture, text=True, shell=True, env=env)
    else:
        result = subprocess.run(args, capture_output=capture, text=True, env=env)
    if check and result.returncode != 0:
        print(f"\n[ERROR] Command exited {result.returncode}")
        if result.stdout:
            print(result.stdout[-3000:])
        if result.stderr:
            print(result.stderr[-3000:])
        sys.exit(1)
    return result


def parse_env(path: Path) -> dict[str, str]:
    """Parse a .env file into {KEY: value}."""
    env: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


# ─── Deployment steps ─────────────────────────────────────────────────────────

def preflight_checks() -> dict[str, str]:
    """Verify tools are available, user is authenticated, and .env exists."""
    header("Pre-flight Checks")

    # Azure CLI
    print("  Checking Azure CLI ...")
    r = run(["az", "--version"], check=False)
    if r.returncode != 0:
        fail("Azure CLI not found. Install from https://aka.ms/installazurecliwindows")
    ok("Azure CLI available")

    # Azure authentication
    print("  Checking Azure auth ...")
    r = run(["az", "account", "show", "--output", "json"], check=False)
    if r.returncode != 0:
        print("    Not logged in — launching az login ...")
        run(["az", "login"], capture=False)
        r = run(["az", "account", "show", "--output", "json"])
    account = json.loads(r.stdout)
    ok(f"Signed in as {account.get('user', {}).get('name', '?')}")

    # Subscription
    print(f"  Setting subscription {SUBSCRIPTION_ID} ...")
    run(["az", "account", "set", "--subscription", SUBSCRIPTION_ID])
    ok("Subscription set")

    # .env file
    if not ENV_FILE.exists():
        fail(f".env not found at {ENV_FILE}. Copy .env.azure and fill in your credentials.")
    ok(f".env found")

    return {}


def deploy_infrastructure() -> dict[str, str]:
    """Deploy or update Azure infrastructure via Bicep. Returns deployment outputs."""
    header("Infrastructure Deployment (Bicep)")

    print(f"  Creating resource group '{RESOURCE_GROUP}' ...")
    run([
        "az", "group", "create",
        "--name", RESOURCE_GROUP,
        "--location", LOCATION,
        "--output", "none",
    ])
    ok("Resource group ready")

    print("  Validating Bicep template ...")
    r = run([
        "az", "deployment", "group", "validate",
        "--resource-group", RESOURCE_GROUP,
        "--template-file", str(BICEP_MAIN),
        "--parameters", str(BICEP_PARAMS),
        "--output", "none",
    ], check=False)
    if r.returncode != 0:
        print(r.stderr)
        fail("Bicep validation failed. Fix the errors above before deploying.")
    ok("Template valid")

    print("  Deploying infrastructure (this takes ~10–15 min on first run) ...")
    result = run([
        "az", "deployment", "group", "create",
        "--resource-group", RESOURCE_GROUP,
        "--name", DEPLOYMENT_NAME,
        "--template-file", str(BICEP_MAIN),
        "--parameters", str(BICEP_PARAMS),
        "--output", "json",
    ])

    deployment = json.loads(result.stdout)
    raw_outputs = deployment.get("properties", {}).get("outputs", {})

    def out(key: str) -> str:
        return raw_outputs.get(key, {}).get("value", "")

    registry_name = out("containerRegistryName")
    keyvault_name = out("keyVaultName")
    container_app_name = out("containerAppName") or _infer_container_app_name()
    app_fqdn = out("containerAppFqdn")

    outputs = {
        "registry_name": registry_name,
        "registry_login_server": f"{registry_name}.azurecr.io",
        "keyvault_name": keyvault_name,
        "keyvault_uri": f"https://{keyvault_name}.vault.azure.net/",
        "container_app_name": container_app_name,
        "app_fqdn": app_fqdn,
        "app_url": f"https://{app_fqdn}" if app_fqdn else "",
    }

    ok(f"Registry:      {outputs['registry_login_server']}")
    ok(f"Key Vault:     {outputs['keyvault_name']}")
    ok(f"Container App: {outputs['container_app_name']}")
    ok(f"App URL:       {outputs['app_url']}")

    return outputs


def _infer_container_app_name() -> str:
    """Fallback: query Azure for the container app in the resource group."""
    r = run([
        "az", "containerapp", "list",
        "--resource-group", RESOURCE_GROUP,
        "--query", "[0].name",
        "--output", "tsv",
    ], check=False)
    return r.stdout.strip() if r.returncode == 0 else "aireceptionist-app"


def build_and_push_image(registry_login_server: str) -> str:
    """Queue an ACR cloud build, poll until done, return the full image tag."""
    header("ACR Cloud Build & Push")

    acr_name = registry_login_server.split(".")[0]
    image_tag = f"{registry_login_server}/{IMAGE_NAME}:latest"

    print(f"  Queuing build in ACR '{acr_name}' (uploading ~280 MB context) ...")
    # --no-wait avoids streaming logs back through Windows console (cp1252 crash).
    result = run([
        "az", "acr", "build",
        "--registry", acr_name,
        "--image", f"{IMAGE_NAME}:latest",
        "--file", str(PROJECT_ROOT / "Dockerfile"),
        "--no-wait",
        str(PROJECT_ROOT),
    ])
    ok("Build queued in Azure")

    # Poll the latest run until it succeeds or fails (max 30 min).
    print("  Polling build status ...")
    for attempt in range(60):
        time.sleep(30)
        r = run([
            "az", "acr", "task", "list-runs",
            "--registry", acr_name,
            "--top", "1",
            "--query", "[0].{status:status,runId:runId}",
            "--output", "json",
        ], check=False)
        if r.returncode != 0 or not r.stdout.strip():
            print(f"    [{attempt+1}/60] Could not query run status, retrying ...")
            continue
        info = json.loads(r.stdout)
        status = info.get("status", "Unknown")
        run_id = info.get("runId", "?")
        print(f"    [{attempt+1}/60] Run {run_id}: {status}")
        if status == "Succeeded":
            ok(f"Image built and pushed -> {image_tag}")
            return image_tag
        if status in ("Failed", "Canceled", "Error"):
            fail(f"ACR build {run_id} failed with status: {status}")

    fail("ACR build timed out after 30 minutes")


def configure_keyvault_secrets(keyvault_name: str) -> None:
    """Push API keys and credentials from .env into Azure Key Vault."""
    header("Key Vault Secret Configuration")

    env = parse_env(ENV_FILE)

    for env_key, secret_name in KEYVAULT_SECRETS_MAP.items():
        value = env.get(env_key, "")
        if not value:
            warn(f"Skipping {secret_name} — {env_key} not set in .env")
            continue
        run([
            "az", "keyvault", "secret", "set",
            "--vault-name", keyvault_name,
            "--name", secret_name,
            "--value", value,
            "--output", "none",
        ])
        ok(f"Secret set: {secret_name}")

    # DATABASE_URL is also a secret
    db_url = env.get("DATABASE_URL", "")
    if db_url:
        run([
            "az", "keyvault", "secret", "set",
            "--vault-name", keyvault_name,
            "--name", "DATABASE-URL",
            "--value", db_url,
            "--output", "none",
        ])
        ok("Secret set: DATABASE-URL")


def update_container_app(container_app_name: str, image_tag: str, infra: dict[str, str]) -> None:
    """Update the Container App with the new image, env vars, and Key Vault secret refs."""
    header("Container App Update")

    env = parse_env(ENV_FILE)

    # Wire Key Vault secrets as Container App secret references (idempotent).
    identity_id = (
        f"/subscriptions/{SUBSCRIPTION_ID}/resourcegroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.ManagedIdentity/userAssignedIdentities"
        f"/{container_app_name.replace('-app', '-identity')}"
    )
    kv_base = infra["keyvault_uri"].rstrip("/") + "/secrets"
    kv_secrets = [
        f"groq-api-key=keyvaultref:{kv_base}/GROQ-API-KEY,identityref:{identity_id}",
        f"sarvam-api-key=keyvaultref:{kv_base}/SARVAM-API-KEY,identityref:{identity_id}",
        f"twilio-account-sid=keyvaultref:{kv_base}/TWILIO-ACCOUNT-SID,identityref:{identity_id}",
        f"twilio-auth-token=keyvaultref:{kv_base}/TWILIO-AUTH-TOKEN,identityref:{identity_id}",
        f"exotel-sid=keyvaultref:{kv_base}/EXOTEL-SID,identityref:{identity_id}",
        f"exotel-token=keyvaultref:{kv_base}/EXOTEL-TOKEN,identityref:{identity_id}",
        f"calcom-api-key=keyvaultref:{kv_base}/CALCOM-API-KEY,identityref:{identity_id}",
    ]
    print(f"  Wiring Key Vault secrets into '{container_app_name}' ...")
    run([
        "az", "containerapp", "secret", "set",
        "--name", container_app_name,
        "--resource-group", RESOURCE_GROUP,
        "--secrets", *kv_secrets,
        "--output", "none",
    ])
    ok("Key Vault secret references set")

    env_vars: list[str] = []
    for key in CONTAINER_ENV_KEYS:
        value = env.get(key, "")
        if value:
            env_vars.append(f"{key}={value}")

    env_vars.append(f"KEYVAULT_URI={infra['keyvault_uri']}")
    # Expose KV-backed secrets as env vars via secretRef.
    env_vars += [
        "GROQ_API_KEY=secretref:groq-api-key",
        "SARVAM_API_KEY=secretref:sarvam-api-key",
        "TWILIO_ACCOUNT_SID=secretref:twilio-account-sid",
        "TWILIO_AUTH_TOKEN=secretref:twilio-auth-token",
        "EXOTEL_SID=secretref:exotel-sid",
        "EXOTEL_TOKEN=secretref:exotel-token",
        "CALCOM_API_KEY=secretref:calcom-api-key",
    ]

    print(f"  Updating '{container_app_name}' with new image ...")
    cmd = [
        "az", "containerapp", "update",
        "--name", container_app_name,
        "--resource-group", RESOURCE_GROUP,
        "--image", image_tag,
        "--output", "none",
    ]
    if env_vars:
        cmd += ["--set-env-vars"] + env_vars

    run(cmd)
    ok("Container App updated — new revision created")


def verify_health(app_url: str, retries: int = 12, interval: int = 15) -> bool:
    """Poll /health until the app responds with status=ok or retries are exhausted."""
    header("Health Verification")

    if not app_url:
        warn("No app URL available — skipping health check")
        return False

    health_url = f"{app_url}/health"
    print(f"  Polling {health_url}  (up to {retries * interval}s) ...")

    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(health_url, timeout=10) as resp:
                data = json.loads(resp.read())
                if data.get("status") == "ok":
                    ok(f"App healthy: {data}")
                    return True
        except Exception as exc:
            print(f"    [{attempt}/{retries}] Not ready yet ({exc})")
            if attempt < retries:
                time.sleep(interval)

    warn(f"App did not report healthy within {retries * interval}s — check Container App logs")
    return False


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    global RESOURCE_GROUP

    parser = argparse.ArgumentParser(description="Deploy AI Receptionist to Azure Container Apps")
    parser.add_argument("--skip-infra", action="store_true", help="Skip Bicep infrastructure deployment")
    parser.add_argument("--skip-build", action="store_true", help="Skip Docker build and push")
    parser.add_argument("--skip-secrets", action="store_true", help="Skip Key Vault secret configuration")
    parser.add_argument("--resource-group", help="Override resource group name")
    parser.add_argument("--registry", help="Override ACR login server (required when --skip-infra)")
    parser.add_argument("--keyvault", help="Override Key Vault name (required when --skip-infra)")
    parser.add_argument("--app-name", help="Override Container App name (required when --skip-infra)")
    parser.add_argument("--app-url", help="Override app URL for health check")
    args = parser.parse_args()

    if args.resource_group:
        RESOURCE_GROUP = args.resource_group

    print()
    print("  AI Receptionist - Azure Deployment Agent")
    print("  Target: Azure Container Apps, Central India")
    print(f"  Resource group: {RESOURCE_GROUP}")

    preflight_checks()

    if args.skip_infra:
        if not (args.registry and args.keyvault and args.app_name):
            fail("--skip-infra requires --registry, --keyvault, and --app-name")
        registry_name = args.registry.split(".")[0]
        registry_login_server = args.registry if ".azurecr.io" in args.registry else f"{registry_name}.azurecr.io"
        infra = {
            "registry_name": registry_name,
            "registry_login_server": registry_login_server,
            "keyvault_name": args.keyvault,
            "keyvault_uri": f"https://{args.keyvault}.vault.azure.net/",
            "container_app_name": args.app_name,
            "app_fqdn": (args.app_url or "").removeprefix("https://"),
            "app_url": args.app_url or "",
        }
        header("Infrastructure (skipped)")
        ok("Using provided values")
    else:
        infra = deploy_infrastructure()

    image_tag = f"{infra['registry_login_server']}/{IMAGE_NAME}:latest"

    if not args.skip_build:
        image_tag = build_and_push_image(infra["registry_login_server"])
    else:
        header("Docker Build & Push (skipped)")
        ok(f"Using existing image: {image_tag}")

    if not args.skip_secrets:
        configure_keyvault_secrets(infra["keyvault_name"])
    else:
        header("Key Vault Secrets (skipped)")

    update_container_app(infra["container_app_name"], image_tag, infra)

    app_url = args.app_url or infra.get("app_url", "")
    healthy = verify_health(app_url)

    header("Deployment Complete")
    print(f"  App URL:    {app_url}")
    print(f"  Key Vault:  {infra['keyvault_uri']}")
    print(f"  Status:     {'[HEALTHY]' if healthy else '[CHECK LOGS]'}")
    print()

    if not healthy:
        print("  To check logs:")
        print(f"    az containerapp logs show --name {infra['container_app_name']} --resource-group {RESOURCE_GROUP} --follow")
        print()


if __name__ == "__main__":
    main()
