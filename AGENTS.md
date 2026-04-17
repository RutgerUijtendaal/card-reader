# AGENTS.md - Card Reader Monorepo

## Purpose
This repository is a backend-first card parsing platform with a Vue web UI and Tauri desktop shell.

Core stack:
- Monorepo tooling: `pnpm` workspaces + `turbo`
- Frontend: Vue 3 + Vite + TypeScript
- Desktop shell: Tauri (Rust)
- Shared Core: Python package (`card_core`) for runtime/data foundations
- Backend API: Python + FastAPI + SQLModel + SQLite (FTS5)
- Parser: Python background parsing processor
- OCR/CV target: PaddleOCR + OpenCV (adapter scaffolded)

## Repo Structure
- `apps/web`: Vue app (`/import-jobs`, `/cards`, `/review`)
- `apps/desktop`: Tauri wrapper; starts sidecar binaries (`card-reader-api`, `card-reader-parser`)
- `services/core`: shared runtime/data modules in `src/card_core`
  - `settings`: env/config + storage paths
  - `logging`: shared logging configuration
  - `database`: DB connection/session/bootstrap
  - `models`: SQLModel entities
  - `repositories`: data access + import job lifecycle helpers
  - `templates`: template store contract (`TemplateStore`)
- `services/api`: FastAPI service
  - `api_http`: routes/controllers/request DTOs/mappers
  - `services`: API-facing use-cases
  - `main.py`: API app entrypoint
- `services/parser`: async polling parser process
  - `parsers`: OCR/crop pipeline
  - `template_store.py`: file-backed template implementation
  - `services`: parser job processor
- `packages/contracts`: OpenAPI-generated TypeScript contracts/client placeholder
- `packages/config`: shared lint/format/tsconfig defaults
- `scripts`: shell scripts for bootstrap/dev/release

## Architectural Rules
- Keep service boundaries strict:
  - `api` depends on `card_core`; never imports parser modules
  - `parser` depends on `card_core`; never imports api modules
  - `card_core` contains shared runtime/data foundations only
- Import flow must remain async:
  - API creates jobs and items
  - Parser claims queued jobs and processes files
- Persist imported images under the configured storage root using hash-based filenames.
- Keep parser provider-agnostic: PaddleOCR is default behind parser-owned adapter boundaries.

## Development Commands
From repo root:
- Install deps: `./scripts/bootstrap.sh --node --python`
- Dev default (no desktop): `./scripts/dev.sh`
- Dev all (including desktop): `pnpm dev:all`
- Desktop dev: `pnpm dev:desktop` (requires Rust/Cargo)
- Build all: `pnpm build`
- Lint all: `pnpm lint`
- Typecheck all: `pnpm typecheck`
- Test all: `pnpm test`

Targeted dev commands:
- API: `pnpm --filter @card-reader/api dev`
- Parser: `pnpm --filter @card-reader/parser dev`
- Core: `pnpm --filter @card-reader/core lint` / `typecheck`
- Web: `pnpm --filter @card-reader/web dev`
- Desktop: `pnpm dev:desktop`

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
- Keep search index (`card_version_search` FTS5) in sync when card text fields change.
- If adding parser file templates, place them under `services/parser/src/parsers/templates` and version IDs clearly.
- Keep template loading behind the `card_core.templates.TemplateStore` contract so DB-backed templates can be added later.
