#!/usr/bin/env bash
# AWS Deployment Script: VND dashboard/API on EC2/Lightsail.
#
# AWS runs Docker Compose for Streamlit + FastAPI only.
# LM Studio, Playwright, and marketplace publishing run on the local Windows PC.

set -euo pipefail

REPO_URL="${1:-https://github.com/sokolowskij/vnd.git}"
REPO_BRANCH="${REPO_BRANCH:-master}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/vnd}"

echo "Starting VND AWS dashboard/API deployment"
echo "Repo:   $REPO_URL"
echo "Branch: $REPO_BRANCH"
echo "Dir:    $DEPLOY_DIR"

echo "Step 1: Install system packages"
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg git

echo "Step 2: Install Docker Engine and Compose plugin"
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /tmp/vnd-docker-keyrings
  curl -fsSL https://get.docker.com -o /tmp/vnd-get-docker.sh
  sudo sh /tmp/vnd-get-docker.sh
  rm -f /tmp/vnd-get-docker.sh
fi

sudo usermod -aG docker "$USER" || true
sudo systemctl enable --now docker

echo "Step 3: Clone or update repository"
sudo mkdir -p "$DEPLOY_DIR"
sudo chown -R "$USER:$USER" "$DEPLOY_DIR"

if [ ! -d "$DEPLOY_DIR/.git" ]; then
  git clone --branch "$REPO_BRANCH" --single-branch "$REPO_URL" "$DEPLOY_DIR"
else
  cd "$DEPLOY_DIR"
  git fetch origin "$REPO_BRANCH"
  git reset --hard "origin/$REPO_BRANCH"
fi

cd "$DEPLOY_DIR"

echo "Step 4: Create .env if missing"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created $DEPLOY_DIR/.env"
  echo "Edit it later for retention/session/backup settings if needed."
fi

chmod +x scripts/*.sh

echo "Step 5: Build and start lightweight AWS containers"
BUILD=1 ./scripts/aws-start.sh

echo ""
echo "Deployment complete"
echo "Dashboard: http://$(hostname -I | awk '{print $1}'):8501"
echo "Backend:   http://$(hostname -I | awk '{print $1}'):8000/health"
echo ""
echo "Useful commands:"
echo "  cd $DEPLOY_DIR"
echo "  docker compose ps"
echo "  docker compose logs -f backend"
echo "  docker compose logs -f frontend"
