#!/usr/bin/env bash
set -euo pipefail

# Keep Node/Python deps aligned before building.
./scripts/bootstrap.sh --node --python

pnpm build
