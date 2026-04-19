# AGENTS.md - Card Reader Monorepo

## Purpose
This repository is a backend-first card parsing platform with a Vue web UI and Tauri desktop shell.

Core stack:
- Monorepo tooling: `pnpm` workspaces + `turbo`
- Frontend: Vue 3 + Vite + TypeScript
- Desktop shell: Tauri (Rust)
- Shared Core: Python service package for runtime/data foundations
- Backend API: Python + FastAPI + SQLModel + SQLite (FTS5)
- Parser: Python background parsing processor
- OCR/CV target: PaddleOCR + OpenCV

## Repo Structure
- `apps/web`: Vue app (`/import-jobs`, `/cards`, `/settings`)
- `apps/desktop`: Tauri wrapper; starts sidecar binaries (`card-reader-api`, `card-reader-parser`)
- `services/core`: shared runtime/data modules in `src/`
  - `settings.py`, `core_logging.py`, `storage.py`, `templates.py`
  - `database/`, `models/`, `repositories/`
- `services/api`: FastAPI service
  - `main.py` (lifespan startup)
  - `controllers/`, `dependencies/`, `mappers/`, `router/`, `schemas/`, `services/`, `seeds/`
  - `database_migrations.py` + Alembic migrations under `alembic/`
- `services/parser`: async polling parser process
  - `main.py` loop
  - `parsers/` (region parsers, OCR runner, symbol detector)
  - `extractors/` + `services/` + `template_store.py` (DB-backed template store)
- `services/integration`: cross-service integration tests (real OCR full-flow fixture cases)
- `scripts`: shell scripts for bootstrap/dev/release

## Architectural Rules
- Keep service boundaries strict:
  - `api` depends on `core`; never imports parser modules
  - `parser` depends on `core`; never imports api modules
  - `core` contains shared runtime/data foundations only
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
- Integration tests: `pnpm --filter @card-reader/integration test`
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
  - tests: `vitest`

## API Surface (v1)
- `POST /imports/upload`
- `GET /imports`
- `GET /imports/{job_id}`
- `GET /cards`
- `GET /cards/filters`
- `GET /cards/{card_id}`
- `GET /cards/{card_id}/generations`
- `GET /cards/{card_id}/image`
- `GET /cards/{card_id}/versions/{version_id}/image`
- `GET /symbols/assets/{asset_path}`
- `GET /exports/csv`
- `GET/POST/PATCH/DELETE /settings/*` (catalog metadata, templates, maintenance, symbol assets)

## Notes for Future Agents
- No auth/multi-user assumptions in v1.
- SQLite is default persistence; do not introduce Postgres-only behavior without explicit request.
- Preserve idempotent import behavior by image hash.
- Keep search index (`card_version_search` FTS5) in sync when card text fields change.
- Template definitions are DB-backed (`template` table) and seeded from `services/api/src/seeds/templates.json`.
- Keep template loading behind `core.templates.TemplateStore`.
