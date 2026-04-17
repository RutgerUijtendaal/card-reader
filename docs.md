# Running Locally

1. `./scripts/bootstrap.sh --node --python`
2. `./scripts/dev.sh`

## Services
- API: `pnpm --filter @card-reader/api dev`
- Worker: `pnpm --filter @card-reader/worker dev`
- Web: `pnpm --filter @card-reader/web dev`
- Desktop: `pnpm --filter @card-reader/desktop dev`
