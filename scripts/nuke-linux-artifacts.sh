#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Nuking Linux/WSL build artifacts in: $ROOT_DIR"

# Python virtual environments that may contain Linux-only layout (e.g. lib64).
rm -rf services/core/.venv
rm -rf services/api/.venv
rm -rf services/parser/.venv

# Node artifacts that can contain wrong-platform binaries (e.g. esbuild ELF).
find . -type d -name node_modules -prune -exec rm -rf {} +
rm -rf .pnpm-store

# Common Python caches.
find . -type d -name __pycache__ -prune -exec rm -rf {} +
find . -type d -name .pytest_cache -prune -exec rm -rf {} +
find . -type d -name .mypy_cache -prune -exec rm -rf {} +
find . -type d -name .ruff_cache -prune -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Rust/Tauri outputs can also be cross-platform incompatible.
rm -rf apps/desktop/src-tauri/target

echo "Done. Reinstall with:"
echo "  pnpm install"
echo "  uv sync --project services/core --extra dev"
echo "  uv sync --project services/api --extra dev"
echo "  uv sync --project services/parser --extra dev"
