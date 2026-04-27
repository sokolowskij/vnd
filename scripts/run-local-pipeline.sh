#!/usr/bin/env bash
# Bash equivalent of scripts/run-local-pipeline.ps1.
#
# Examples:
#   ./scripts/run-local-pipeline.sh
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

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DATA_DIR="./data/products"
MODE="dry_run"
MARKETPLACES=("olx" "facebook")
RECALCULATE=0
YES=0
INSTALL_BROWSERS=0

usage() {
  sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
}

split_marketplaces() {
  local raw="$1"
  raw="${raw//,/ }"
  # shellcheck disable=SC2206
  MARKETPLACES=($raw)
}

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
  echo "DataDir does not exist: $DATA_DIR"
  exit 1
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
  CLI_ARGS+=(--use-cached-listings)
fi

"$PYTHON" "${CLI_ARGS[@]}"
