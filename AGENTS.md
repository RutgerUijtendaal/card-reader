# AGENTS.md - Card Reader Monorepo

## Purpose
This repository is a backend-first card parsing platform with a Vue web UI and Tauri desktop shell.

Core stack:
- Monorepo tooling: `pnpm` workspaces + `turbo`
- Frontend: Vue 3 + Vite + TypeScript
- Desktop shell: Tauri (Rust)
- Backend API: Python + FastAPI + SQLModel + SQLite (FTS5)
- Worker: Python background job processor
- OCR/CV target: PaddleOCR + OpenCV (adapter scaffolded)

## Repo Structure
- `apps/web`: Vue app (`/import-jobs`, `/cards`, `/review`)
- `apps/desktop`: Tauri wrapper; starts sidecar binaries (`card-reader-api`, `card-reader-worker`)
- `services/api`: FastAPI service and domain/application/infrastructure/interfaces layers
- `services/worker`: async polling worker processing queued import jobs
- `packages/contracts`: OpenAPI-generated TypeScript contracts/client placeholder
- `packages/config`: shared lint/format/tsconfig defaults
- `scripts`: shell scripts for bootstrap/dev/release

## Architectural Rules
- Keep API logic layered:
  - `domain`: pure business concepts
  - `application`: orchestration/use-cases
  - `infrastructure`: DB/OCR/storage integrations
  - `interfaces/http`: request/response contracts and routes
- Import flow must remain async:
  - API creates jobs and items
  - Worker claims queued jobs and processes files
- Persist imported images under app data using hash-based filenames.
- Keep parser provider-agnostic: PaddleOCR is default, but behind adapter boundaries.

## Development Commands
From repo root:
- Install deps: `./scripts/bootstrap.sh --node --python`
- Dev all (turbo): `./scripts/dev.sh`
- Build all: `pnpm build`
- Lint all: `pnpm lint`
- Typecheck all: `pnpm typecheck`
- Test all: `pnpm test`

Targeted dev commands:
- API: `pnpm --filter @card-reader/api dev`
- Worker: `pnpm --filter @card-reader/worker dev`
- Web: `pnpm --filter @card-reader/web dev`
- Desktop: `pnpm --filter @card-reader/desktop dev`

## Coding Standards
- Python:
  - dependency/runtime via `uv`
  - lint: `ruff`
  - typing: `mypy` (strict)
  - tests: `pytest`
- TypeScript/Vue:
  - lint: `eslint`
  - format: `prettier`
  - typecheck: `vue-tsc`
  - tests: `vitest`, `playwright` (smoke)

## API Surface (v1)
- `POST /imports`
- `GET /imports`
- `GET /imports/{job_id}`
- `GET /cards`
- `GET /cards/{card_id}`
- `PATCH /cards/{card_id}`
- `GET /exports/csv`

## Notes for Future Agents
- No auth/multi-user assumptions in v1.
- SQLite is default persistence; do not introduce Postgres-only behavior without explicit request.
- Preserve idempotent import behavior by image hash.
- Keep search index (`card_search` FTS5) in sync when card text fields change.
- If adding new parser templates, place them under `services/api/src/card_reader_api/infrastructure/templates` and version their IDs clearly.
