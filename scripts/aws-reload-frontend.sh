#!/usr/bin/env bash
# Reload only the AWS Streamlit frontend.
#
# Default behavior:
# - runs from /opt/agentic-seller
# - pulls the latest git changes with --ff-only
# - rebuilds and recreates only the frontend container
# - keeps backend and Docker volumes untouched
#
# Useful overrides:
#   AGENTIC_SELLER_DIR=/opt/agentic-seller
#   PULL_LATEST=0
#   USE_PROD_COMPOSE=1

set -euo pipefail

DEPLOY_DIR="${AGENTIC_SELLER_DIR:-/opt/agentic-seller}"
PULL_LATEST="${PULL_LATEST:-1}"
USE_PROD_COMPOSE="${USE_PROD_COMPOSE:-0}"

cd "$DEPLOY_DIR"

compose_args=(-f docker-compose.yml)
if [[ "$USE_PROD_COMPOSE" == "1" && -f docker-compose.prod.yml ]]; then
  compose_args+=(-f docker-compose.prod.yml)
fi

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "${compose_args[@]}" "$@"
  else
    docker-compose "${compose_args[@]}" "$@"
  fi
}

echo "Reloading frontend in $DEPLOY_DIR"

if [[ "$PULL_LATEST" == "1" && -d .git ]]; then
  echo "Pulling latest code with git pull --ff-only..."
  git pull --ff-only
else
  echo "Skipping git pull."
fi

echo "Building frontend image..."
compose build frontend

echo "Recreating frontend container..."
compose up -d --no-deps frontend

echo "Waiting for Streamlit health check..."
for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:8501/_stcore/health >/dev/null 2>&1; then
    echo "Frontend is healthy: http://127.0.0.1:8501"
    compose ps frontend
    exit 0
  fi
  sleep 2
done

echo "Frontend did not become healthy in time. Recent logs:"
compose logs --tail=80 frontend
exit 1
