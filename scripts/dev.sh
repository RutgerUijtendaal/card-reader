#!/usr/bin/env bash
set -euo pipefail

# Keep Python envs aligned with pyproject changes before starting long-running dev processes.
./scripts/bootstrap.sh --python

pnpm dev
