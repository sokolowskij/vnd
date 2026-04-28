#!/usr/bin/env bash
# Run the product pipeline on AWS data while using LM Studio from your local PC.
#
# First, on your Windows machine, open the reverse tunnel:
#   ./scripts/open-lmstudio-aws-tunnel.ps1
#
# Then, on AWS:
#   cd /opt/vnd
#   ./scripts/aws-run-local-lm-pipeline.sh
#
# Useful overrides:
#   MODE=dry_run
#   MARKETPLACES="olx facebook"
#   DATA_DIR=/app/data/products
#   LM_STUDIO_TUNNEL_PORT=1234
#   REBUILD=1
#   USE_PROD_COMPOSE=1
#   AUTH_MODE=1

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOY_DIR="${AGENTIC_SELLER_DIR:-$DEFAULT_DEPLOY_DIR}"
MODE="${MODE:-dry_run}"
MARKETPLACES="${MARKETPLACES:-olx facebook}"
DATA_DIR="${DATA_DIR:-/app/data/products}"
LM_STUDIO_TUNNEL_PORT="${LM_STUDIO_TUNNEL_PORT:-1234}"
USE_PROD_COMPOSE="${USE_PROD_COMPOSE:-0}"
REBUILD="${REBUILD:-0}"
AUTH_MODE="${AUTH_MODE:-0}"

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

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

LOCAL_MODEL_API="http://127.0.0.1:${LM_STUDIO_TUNNEL_PORT}/v1"
OPENAI_API_KEY="${OPENAI_API_KEY:-local-model}"
OPENAI_MODEL="${OPENAI_MODEL:-google/gemma-4-e4b}"

echo "Checking LM Studio tunnel at $LOCAL_MODEL_API/models"
if ! curl -fsS "$LOCAL_MODEL_API/models" >/dev/null; then
  echo "Cannot reach LM Studio through the SSH tunnel."
  echo "On your Windows machine, run and keep open:"
  echo "  powershell -ExecutionPolicy Bypass -File .\\scripts\\open-lmstudio-aws-tunnel.ps1"
  exit 1
fi

if [[ "$REBUILD" == "1" ]]; then
  compose build backend
fi

compose up -d backend

backend_container="$(compose ps -q backend)"
if [[ -z "$backend_container" ]]; then
  echo "Backend container is not running."
  exit 1
fi

backend_image="$(compose images -q backend | head -n 1)"
if [[ -z "$backend_image" ]]; then
  echo "Could not determine backend image. Try REBUILD=1 ./scripts/aws-run-local-lm-pipeline.sh"
  exit 1
fi

read -r -a marketplace_args <<< "$MARKETPLACES"

echo "Running pipeline on AWS data:"
echo "  Data dir:      $DATA_DIR"
echo "  Mode:          $MODE"
echo "  Marketplaces:  $MARKETPLACES"
echo "  Model API:     $LOCAL_MODEL_API"

cli_args=(
  python -m agentic_seller.cli
  --data-dir "$DATA_DIR"
  --mode "$MODE"
  --marketplaces "${marketplace_args[@]}"
)

if [[ "$AUTH_MODE" == "1" ]]; then
  cli_args+=(--auth-mode)
fi

docker run --rm \
  --network host \
  --volumes-from "$backend_container" \
  -e LOCAL_MODEL_API="$LOCAL_MODEL_API" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e OPENAI_MODEL="$OPENAI_MODEL" \
  -e DEFAULT_CURRENCY="${DEFAULT_CURRENCY:-PLN}" \
  -e POST_MODE="$MODE" \
  -e HEADLESS="${HEADLESS:-true}" \
  -e ENABLE_OLX="${ENABLE_OLX:-true}" \
  -e ENABLE_FACEBOOK="${ENABLE_FACEBOOK:-true}" \
  -e USER_DATA_DIR="${USER_DATA_DIR:-/app/data/browser_profiles}" \
  "$backend_image" \
  "${cli_args[@]}"
