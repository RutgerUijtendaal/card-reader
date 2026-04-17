#!/usr/bin/env bash
set -euo pipefail

pnpm build
echo "Release artifacts built. Add desktop signing in CI/release pipeline."
