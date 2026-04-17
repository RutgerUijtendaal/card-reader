#!/usr/bin/env bash
set -euo pipefail

INSTALL_NODE_DEPS=false
INSTALL_PYTHON_DEPS=false

if [[ $# -eq 0 ]]; then
  INSTALL_NODE_DEPS=true
  INSTALL_PYTHON_DEPS=true
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --node)
      INSTALL_NODE_DEPS=true
      ;;
    --python)
      INSTALL_PYTHON_DEPS=true
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: ./scripts/bootstrap.sh [--node] [--python]"
      exit 1
      ;;
  esac
  shift
done

require_cmd() {
  local cmd="$1"
  local hint="$2"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Required command '$cmd' not found. $hint"
    exit 1
  fi
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export UV_CACHE_DIR="$REPO_ROOT/.uv-cache"
mkdir -p "$UV_CACHE_DIR"

if [[ "$INSTALL_NODE_DEPS" == "true" ]]; then
  require_cmd pnpm "Install pnpm first (npm install -g pnpm)."
  pnpm install
fi

if [[ "$INSTALL_PYTHON_DEPS" == "true" ]]; then
  require_cmd uv "Install uv first (curl -LsSf https://astral.sh/uv/install.sh | sh)."
  (cd "$REPO_ROOT/services/api" && uv sync --extra dev)
  (cd "$REPO_ROOT/services/worker" && uv sync --extra dev)
fi

echo "Bootstrap complete."
