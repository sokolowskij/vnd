#!/usr/bin/env bash
# Bash equivalent of scripts/run-local-pipeline.ps1.
#
# Examples:
#   ./scripts/run-local-pipeline.sh
#   MODE=dry_run MARKETPLACES="facebook" ./scripts/run-local-pipeline.sh
#   ./scripts/run-local-pipeline.sh -Mode dry_run -DataDir ./data/products
#   ./scripts/run-local-pipeline.sh -Mode publish -Marketplaces facebook
#   ./scripts/run-local-pipeline.sh -Mode publish -Marketplaces facebook -Recalculate
#   ./scripts/run-local-pipeline.sh -Mode publish -Marketplaces olx,facebook -Yes
#
# Notes:
#   - By default, existing listing_plan.json files are reused as cached data.
#   - Use -Recalculate to regenerate listing_plan.json before posting.
#   - dry_run writes post_results.json without submitting listings.
#   - publish opens/uses marketplace browser automation and may post real listings.
#   - On AWS, if ./data/products does not exist but the backend container is
#     running, this script processes /app/data/products from the Docker volume.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DATA_DIR="${DATA_DIR:-./data/products}"
MODE="${MODE:-dry_run}"
MARKETPLACES_RAW="${MARKETPLACES:-}"
MARKETPLACES=("olx" "facebook")
RECALCULATE=0
YES=0
INSTALL_BROWSERS=0
USE_PROD_COMPOSE="${USE_PROD_COMPOSE:-0}"
REBUILD="${REBUILD:-0}"

usage() {
  sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
}

split_marketplaces() {
  local raw="$1"
  raw="${raw//,/ }"
  # shellcheck disable=SC2206
  MARKETPLACES=($raw)
}

compose_args=(-f docker-compose.yml)
if [[ "$USE_PROD_COMPOSE" == "1" && -f "$REPO_ROOT/docker-compose.prod.yml" ]]; then
  compose_args+=(-f docker-compose.prod.yml)
fi

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "${compose_args[@]}" "$@"
  else
    docker-compose "${compose_args[@]}" "$@"
  fi
}

run_in_backend_data_container() {
  local container_data_dir="${CONTAINER_DATA_DIR:-/app/data/products}"
  local backend_container
  local backend_image

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
    echo "Could not determine backend image. Try REBUILD=1 ./scripts/run-local-pipeline.sh"
    exit 1
  fi

  if ! docker run --rm --volumes-from "$backend_container" "$backend_image" test -d "$container_data_dir"; then
    echo "Container DataDir does not exist: $container_data_dir"
    exit 1
  fi

  local model_api="${LOCAL_MODEL_API:-http://127.0.0.1:1234/v1}"

  echo "Host DataDir does not exist: $DATA_DIR"
  echo "Using backend Docker volume instead."
  echo "Checking model endpoint: $model_api/models"
  if command -v curl >/dev/null 2>&1; then
    if ! curl -fsS "$model_api/models" >/dev/null; then
      echo "Cannot reach model endpoint from AWS host."
      echo "Keep the Windows SSH reverse tunnel open and make sure LM Studio server is running."
      exit 1
    fi
  fi

  echo "Running Agentic Seller pipeline"
  echo "DataDir:      $container_data_dir"
  echo "Mode:         $MODE"
  echo "Marketplaces: ${MARKETPLACES[*]}"
  echo "Model API:    $model_api"
  if [[ "$RECALCULATE" == "1" ]]; then
    echo "Listings:     recalculate"
  else
    echo "Listings:     use cached when available"
  fi

  local cli_args=(
    python -u -m agentic_seller.cli
    --data-dir "$container_data_dir"
    --mode "$MODE"
    --marketplaces "${MARKETPLACES[@]}"
  )

  if [[ "$RECALCULATE" != "1" ]]; then
    if docker run --rm --volumes-from "$backend_container" "$backend_image" \
      python -m agentic_seller.cli --help | grep -q -- "--use-cached-listings"; then
      cli_args+=(--use-cached-listings)
    fi
  fi

  docker run --rm \
    --network host \
    --volumes-from "$backend_container" \
    -e LOCAL_MODEL_API="$model_api" \
    -e PYTHONUNBUFFERED=1 \
    -e OPENAI_API_KEY="${OPENAI_API_KEY:-local-model}" \
    -e OPENAI_MODEL="${OPENAI_MODEL:-google/gemma-4-e4b}" \
    -e DEFAULT_CURRENCY="${DEFAULT_CURRENCY:-PLN}" \
    -e POST_MODE="$MODE" \
    -e HEADLESS="${HEADLESS:-true}" \
    -e ENABLE_OLX="${ENABLE_OLX:-true}" \
    -e ENABLE_FACEBOOK="${ENABLE_FACEBOOK:-true}" \
    -e USER_DATA_DIR="${USER_DATA_DIR:-/app/data/browser_profiles}" \
    "$backend_image" \
    "${cli_args[@]}"
}

if [[ -n "$MARKETPLACES_RAW" ]]; then
  split_marketplaces "$MARKETPLACES_RAW"
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    -DataDir|--data-dir)
      DATA_DIR="${2:-}"
      shift 2
      ;;
    -Mode|--mode)
      MODE="${2:-}"
      shift 2
      ;;
    -Marketplaces|--marketplaces)
      shift
      MARKETPLACES=()
      while [[ $# -gt 0 && "$1" != -* ]]; do
        if [[ "$1" == *","* ]]; then
          split_marketplaces "$1"
        else
          MARKETPLACES+=("$1")
        fi
        shift
      done
      ;;
    -Recalculate|--recalculate)
      RECALCULATE=1
      shift
      ;;
    -Yes|--yes|-y)
      YES=1
      shift
      ;;
    -InstallBrowsers|--install-browsers)
      INSTALL_BROWSERS=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ "$MODE" != "dry_run" && "$MODE" != "publish" ]]; then
  echo "Invalid mode: $MODE. Expected dry_run or publish."
  exit 1
fi

cd "$REPO_ROOT"

if [[ ! -f .env ]]; then
  echo "Missing .env in $REPO_ROOT. Create it from .env.example and configure it first."
  exit 1
fi

PYTHON="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" && -x "$REPO_ROOT/.venv/Scripts/python.exe" ]]; then
  PYTHON="$REPO_ROOT/.venv/Scripts/python.exe"
fi
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python"
fi

if [[ "$INSTALL_BROWSERS" == "1" ]]; then
  "$PYTHON" -m playwright install chromium
fi

if [[ "$MODE" == "publish" && "$YES" != "1" ]]; then
  echo "Publish mode may create real marketplace listings."
  read -r -p "Type PUBLISH to continue: " answer
  if [[ "$answer" != "PUBLISH" ]]; then
    echo "Cancelled."
    exit 1
  fi
fi

if [[ ! -d "$DATA_DIR" ]]; then
  if command -v docker >/dev/null 2>&1 && [[ -f docker-compose.yml ]]; then
    run_in_backend_data_container
    exit 0
  else
    echo "DataDir does not exist: $DATA_DIR"
    exit 1
  fi
fi

RESOLVED_DATA_DIR="$(cd "$DATA_DIR" && pwd)"
export PYTHONPATH="$REPO_ROOT/src"
if [[ -z "${USER_DATA_DIR:-}" || "${USER_DATA_DIR:-}" == "/app/data/browser_profiles" ]]; then
  export USER_DATA_DIR="$REPO_ROOT/browser_profiles"
fi

echo "Running Agentic Seller pipeline"
echo "DataDir:      $RESOLVED_DATA_DIR"
echo "Mode:         $MODE"
echo "Marketplaces: ${MARKETPLACES[*]}"
echo "UserDataDir:  $USER_DATA_DIR"
if [[ "$RECALCULATE" == "1" ]]; then
  echo "Listings:     recalculate"
else
  echo "Listings:     use cached when available"
fi

CLI_ARGS=(
  -m agentic_seller.cli
  --data-dir "$RESOLVED_DATA_DIR"
  --mode "$MODE"
  --marketplaces "${MARKETPLACES[@]}"
)

if [[ "$RECALCULATE" != "1" ]]; then
  if "$PYTHON" -m agentic_seller.cli --help | grep -q -- "--use-cached-listings"; then
    CLI_ARGS+=(--use-cached-listings)
  fi
fi

PYTHONUNBUFFERED=1 "$PYTHON" -u "${CLI_ARGS[@]}"
