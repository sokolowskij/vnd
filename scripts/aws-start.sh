#!/usr/bin/env bash
# Start the AWS Agentic Seller stack.
#
# Default behavior:
# - starts backend and frontend from /opt/agentic-seller
# - keeps existing Docker volumes/state
# - does not rebuild unless BUILD=1 is supplied
#
# Useful overrides:
#   AGENTIC_SELLER_DIR=/opt/agentic-seller
#   BUILD=1
#   USE_PROD_COMPOSE=1

set -euo pipefail

DEPLOY_DIR="${AGENTIC_SELLER_DIR:-/opt/agentic-seller}"
BUILD="${BUILD:-0}"
USE_PROD_COMPOSE="${USE_PROD_COMPOSE:-0}"

cd "$DEPLOY_DIR"

if [[ ! -f .env ]]; then
  echo "Missing $DEPLOY_DIR/.env. Create it from .env.example and configure secrets first."
  exit 1
fi

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

echo "Starting Agentic Seller from $DEPLOY_DIR"

if [[ "$BUILD" == "1" ]]; then
  echo "Building images..."
  compose build
fi

compose up -d

echo "Waiting for backend health check..."
for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    backend_ok=1
    break
  fi
  sleep 2
done

echo "Waiting for frontend health check..."
for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:8501/_stcore/health >/dev/null 2>&1; then
    frontend_ok=1
    break
  fi
  sleep 2
done

compose ps

if [[ "${backend_ok:-0}" != "1" || "${frontend_ok:-0}" != "1" ]]; then
  echo "One or more services did not become healthy. Recent logs:"
  compose logs --tail=120
  exit 1
fi

echo "Agentic Seller is running."
echo "Backend:  http://127.0.0.1:8000"
echo "Frontend: http://127.0.0.1:8501"
