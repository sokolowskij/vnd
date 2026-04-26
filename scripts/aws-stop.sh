#!/usr/bin/env bash
# Stop the AWS Agentic Seller stack without deleting product/review state.
#
# Default behavior uses docker compose stop, which keeps containers and volumes.
# Use REMOVE_CONTAINERS=1 to run docker compose down while still keeping volumes.
#
# Useful overrides:
#   AGENTIC_SELLER_DIR=/opt/agentic-seller
#   REMOVE_CONTAINERS=1
#   USE_PROD_COMPOSE=1

set -euo pipefail

DEPLOY_DIR="${AGENTIC_SELLER_DIR:-/opt/agentic-seller}"
REMOVE_CONTAINERS="${REMOVE_CONTAINERS:-0}"
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

echo "Stopping Agentic Seller in $DEPLOY_DIR"

if [[ "$REMOVE_CONTAINERS" == "1" ]]; then
  compose down
else
  compose stop
fi

compose ps
echo "Stopped. Docker volumes were not removed."
