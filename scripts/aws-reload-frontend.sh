#!/usr/bin/env bash
# Reload the AWS Streamlit frontend and matching backend API image.
#
# Default behavior:
# - runs from the repo root that contains this scripts/ directory
# - pulls the latest git changes with --ff-only
# - rebuilds and recreates backend + frontend containers
# - keeps Docker volumes/data untouched
#
# Useful overrides:
#   AGENTIC_SELLER_DIR=/opt/vnd
#   PULL_LATEST=0
#   USE_PROD_COMPOSE=1
#   FRONTEND_ONLY=1

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOY_DIR="${AGENTIC_SELLER_DIR:-$DEFAULT_DEPLOY_DIR}"
PULL_LATEST="${PULL_LATEST:-1}"
USE_PROD_COMPOSE="${USE_PROD_COMPOSE:-0}"
FRONTEND_ONLY="${FRONTEND_ONLY:-0}"

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

if [[ "$FRONTEND_ONLY" == "1" ]]; then
  services=(frontend)
  echo "Reloading frontend only in $DEPLOY_DIR"
else
  services=(backend frontend)
  echo "Reloading backend and frontend in $DEPLOY_DIR"
fi

if [[ "$PULL_LATEST" == "1" && -d .git ]]; then
  echo "Pulling latest code with git pull --ff-only..."
  git pull --ff-only
else
  echo "Skipping git pull."
fi

echo "Building ${services[*]} image(s)..."
compose build "${services[@]}"

echo "Recreating ${services[*]} container(s)..."
compose up -d --force-recreate "${services[@]}"

echo "Waiting for backend health check..."
for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    backend_ok=1
    break
  fi
  sleep 2
done

echo "Waiting for Streamlit health check..."
for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:8501/_stcore/health >/dev/null 2>&1; then
    frontend_ok=1
    break
  fi
  sleep 2
done

compose ps "${services[@]}"

if [[ "${backend_ok:-0}" == "1" && "${frontend_ok:-0}" == "1" ]]; then
  echo "Reloaded successfully."
  echo "Backend:  http://127.0.0.1:8000"
  echo "Frontend: http://127.0.0.1:8501"
  exit 0
fi

echo "One or more services did not become healthy in time. Recent logs:"
compose logs --tail=100 "${services[@]}"
exit 1
