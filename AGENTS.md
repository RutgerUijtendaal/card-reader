# AGENTS.md - Card Reader Monorepo

## Operating Rules
- Always read this file before working.
- Read `TODO.local.md` for local task context.
- Ask before editing `AGENTS.md`; update it when project guidance changes.
- Update `.gitignore` when adding generated, private, or machine-local files.
- Write scalable, readable code. Fix underlying issues cleanly instead of layering quick fixes.

## Purpose
Card Reader is a Django-backed card parsing platform with a Vue web UI, a Tauri desktop shell, and a
background OCR/parser process.

Core stack:
- Monorepo tooling: `pnpm` workspaces + `turbo`
- Frontend: Vue 3 + Vite + TypeScript
- Desktop shell: Tauri (Rust)
- Shared core: Python package with Django models, migrations, settings, repositories, services, and storage
- Backend API: Django + Django REST Framework + SQLite
- Parser: Python background process using the core Django data layer
- OCR/CV target: PaddleOCR + OpenCV

## Repo Structure
- `apps/web`: Vue app for card gallery, imports, review, settings, and login.
- `apps/desktop`: Tauri wrapper around the web/backend experience.
- `services/core`: shared runtime and domain package.
  - Django models and migrations
  - database connection/adoption helpers
  - repositories and business services
  - shared storage/settings/template utilities
  - `card_reader_core.django_settings` for non-HTTP Django processes
- `services/api`: Django/DRF HTTP service.
  - Django project: `card_reader_api.project`
  - auth endpoints, API views/serializers, URL routing, management commands, seeds
  - API-specific settings extend core Django settings
- `services/parser`: async polling parser process.
  - OCR runner, region parsers, symbol detector, extractors
  - boots Django with `DJANGO_SETTINGS_MODULE=card_reader_core.django_settings`
- `services/integration`: cross-service integration tests for parser/core/API behavior.
- `scripts`: bootstrap/dev/release scripts.

## Architectural Rules
- Keep service boundaries strict:
  - `api` depends on `core`; it must not import parser modules.
  - `parser` depends on `core`; it must not import API views, serializers, URLs, DRF settings, or API-only services.
  - `core` contains shared domain/runtime foundations only.
- Keep shared card filtering logic centralized in `apps/web/src/modules/card-filters`.
  - Route/query parsing, stable key-based filter state, key/id translation, and API filter param building belong there.
  - Page modules such as gallery/review/pickers should only own page-specific behavior like pagination, navigation context, and scroll restoration.
- Django owns the domain schema through migrations in `services/core`.
- SQLite is the default database. Do not introduce Postgres-only behavior without explicit approval.
- Import flow remains async:
  - API creates jobs and items.
  - Parser claims queued work.
  - Parser writes results through core repositories/services.
- Persist imported images under the configured storage root using hash-based filenames.
- Keep parser provider-agnostic. PaddleOCR is the default behind parser-owned adapter boundaries.
- Keep Vue API compatibility stable unless a requested change explicitly requires a contract change.

## Auth Rules
- Auth is enabled by default.
- Card gallery and card assets are public.
- Import jobs, review, settings, catalog, templates, and exports require `is_staff=true`.
- Maintenance endpoints require `is_superuser=true`.
- The Vue app uses Django session auth with CSRF protection.
- `/auth/me` and `/auth/login` return a CSRF token for unsafe browser requests.

## Seed Files
- Default seed JSON files live in `services/api/src/card_reader_api/seeds`:
  - `seed-keywords.json`
  - `seed-symbols.json`
  - `seed-tags.json`
  - `seed-templates.json`
  - `seed-types.json`
  - `seed-users.example.json`
- Local development users live in:
  - `services/api/src/card_reader_api/seeds/seed-users.local.json`
- `seed-users.local.json` is gitignored.

## Docker And Runtime
- `api` and `parser` share the `card_reader_data` Docker volume at `/var/lib/card-reader`.
- API container startup runs migrations, user seeds, default seeds, then Gunicorn.
- Parser container waits for the API health check and assumes the schema is ready.
- Parser container uses `DJANGO_SETTINGS_MODULE=card_reader_core.django_settings`.
- Runtime settings are provided through `CARD_READER_*` environment variables.

## Development Commands
From repo root:
- Install deps: `pnpm setup`
- Install Node deps only: `pnpm deps:js`
- Install Python deps only: `pnpm deps:py`
- Dev default: `pnpm dev`
- Dev all: `pnpm dev:all`
- Desktop dev: `pnpm dev:desktop`
- Build all: `pnpm build`
- Lint all: `pnpm lint`
- Typecheck all: `pnpm typecheck`
- Test all: `pnpm test`

Targeted commands:
- API: `pnpm --filter @card-reader/api dev`
- Parser: `pnpm --filter @card-reader/parser dev`
- Core: `pnpm --filter @card-reader/core lint` / `pnpm --filter @card-reader/core typecheck`
- Web: `pnpm --filter @card-reader/web dev`
- Integration tests: `pnpm --filter @card-reader/integration test`

## Coding Standards
- Python:
  - dependency/runtime via `uv`
  - lint: `ruff`
  - typing: `mypy`
  - tests: `pytest`
- TypeScript/Vue:
  - lint: `eslint`
  - format: `prettier`
  - typecheck: `vue-tsc`
  - tests: `vitest`
  - prefer VueUse composables when they fit cleanly and reduce custom reactive glue

## API Surface
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
- `GET/POST/PATCH/DELETE /settings/*`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `GET /health`

## Notes For Future Agents
- Do not revert unrelated user changes in this dirty worktree.
- Treat the backend as Django/DRF with Django-owned models and migrations.
- Keep README files declarative and current-state focused.
- Do not store real credentials in the app repo.
- Do not read or expose private seed user files unless the user explicitly asks.
