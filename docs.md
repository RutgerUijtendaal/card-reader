# Running Locally

1. `./scripts/bootstrap.sh --node --python`
2. `./scripts/dev.sh`

## Services
- API: `pnpm --filter @card-reader/api dev`
- Parser: `pnpm --filter @card-reader/parser dev`
- Core: `pnpm --filter @card-reader/core lint`
- Web: `pnpm --filter @card-reader/web dev`
- All incl. desktop: `pnpm dev:all`
- Desktop: `pnpm dev:desktop`
