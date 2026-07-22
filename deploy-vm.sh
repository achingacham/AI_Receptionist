#!/bin/bash
# Deploy AI Receptionist to a plain Linux VM (Oracle Cloud, or any other
# host with SSH access and a public IP). Run this ON the VM, from the repo
# root, after copying the code over (git clone / scp / rsync).
#
# What it does:
#   1. Installs Docker + the Compose plugin if missing (apt or dnf/yum).
#   2. Opens ports 80/443 in the VM's local firewall (ufw or firewalld) —
#      note this is separate from the Oracle Cloud Security List / Network
#      Security Group, which you must also open from the OCI console; this
#      script cannot reach cloud-provider firewalls, only the OS-level one.
#   3. Creates ./data for the SQLite volume mount.
#   4. Builds and starts the app + Caddy reverse proxy via docker compose.

set -euo pipefail

echo "==> Checking for Docker"
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not found — installing."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf -y install dnf-plugins-core
    sudo dnf config-manager --add-repo https://download.docker.com/linux/oracle/docker-ce.repo || \
      sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo dnf -y install docker-ce docker-ce-cli containerd.io docker-compose-plugin
  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y yum-utils
    sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  else
    echo "No supported package manager (apt/dnf/yum) found. Install Docker manually." >&2
    exit 1
  fi
  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER" || true
  echo "Docker installed. You may need to log out/in for group membership to take effect."
else
  echo "Docker already installed."
fi

echo "==> Opening ports 80/443 in the local firewall"
if command -v ufw >/dev/null 2>&1 && sudo ufw status | grep -q "Status: active"; then
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
elif command -v firewall-cmd >/dev/null 2>&1 && sudo systemctl is-active --quiet firewalld; then
  sudo firewall-cmd --permanent --add-port=80/tcp
  sudo firewall-cmd --permanent --add-port=443/tcp
  sudo firewall-cmd --reload
else
  echo "No active ufw/firewalld detected — skipping local firewall rules."
fi
echo "Reminder: also open ports 80/443 in the OCI Security List / Network Security Group from the cloud console."

echo "==> Ensuring .env exists"
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    echo "Created .env from .env.example — fill in real API keys before going live."
  else
    echo ".env is missing and there's no .env.example to copy from." >&2
    exit 1
  fi
fi

echo "==> Creating data directory for SQLite persistence"
# The container runs as uid 1000 (see Dockerfile) — the bind mount must be
# owned by that uid or SQLite writes fail with "permission denied" on hosts
# where the deploying user has a different uid (e.g. Ubuntu's default 1001).
mkdir -p data
sudo chown -R 1000:1000 data

echo "==> Building and starting containers"
sudo docker compose up -d --build

echo "==> Done. Checking health"
sleep 3
curl -fsS http://localhost/health && echo || echo "Health check failed — check 'docker compose logs -f'."
