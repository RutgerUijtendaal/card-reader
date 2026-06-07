# AGENTS.md - Card Reader Monorepo

## Operating Rules
- Always read this file before working.
- Ask before editing `AGENTS.md`; update it when project guidance changes.
- Update `.gitignore` when adding generated, private, or machine-local files.
- Write scalable, readable code. Fix underlying issues cleanly instead of layering quick fixes.
- Never write absolute local filesystem paths into committed repository files or docs; use repo-relative paths instead.
- Run lint and typecheck before finishing tasks that touch related source, config, generated code, or typed contracts. For docs-only, diagram-only, or skill-only changes, validate the changed artifact directly instead.

## Purpose
Card Reader is a Django-backed card parsing platform with a Vue web UI and a
background OCR/parser process.

Core stack:
- Monorepo tooling: `pnpm` workspaces + `turbo`
- Frontend: Vue 3 + Vite + TypeScript
- Shared core: Python package with Django models, migrations, settings, repositories, services, and storage
- Backend API: Django + Django REST Framework + SQLite
- Parser: Python background process using the core Django data layer
- OCR/CV target: PaddleOCR + OpenCV

## Repo Structure
- `frontend`: Vue app for card gallery, imports, review, settings, and login.
- `services/core`: shared runtime and domain package.
  - Django models and migrations
  - database connection/adoption helpers
  - feature-scoped repositories and business services
  - shared config, storage, metadata, rule-text, operations, and template utilities
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
- Before adding a new utility, abstraction, workflow, or UI pattern, check whether an existing solution can be extended cleanly.
- Prefer unifying overlapping implementations over introducing parallel ones that solve the same problem in slightly different ways.
- When similar logic exists in multiple places, move toward a shared, well-owned abstraction when the fit is real.
- Do not generalize prematurely, but treat repeated patterns and near-duplicate solutions as a prompt to consolidate.
- Before adding a new dependency, custom utility, or bespoke implementation for a common UI/backend pattern, scan the existing package dependencies and local shared utilities first, and prefer using them when the use-case fits cleanly.
- Backend code follows a layered shape:
  - API views/controllers handle transport concerns, auth, request validation, and response shaping.
  - Core services coordinate domain workflows and call repositories.
  - Core repositories own Django query/write persistence details.
  - Helper classes/modules own grouped normalization, validation, preview-building, or resource-loading logic when that keeps services/repositories focused.
- Keep `card_reader_core` package root minimal. Root files should be limited to package/Django entrypoints such as `__init__.py`, `apps.py`, `django_settings.py`, and `py.typed`.
- Place core runtime/domain helpers in owned packages instead of one-off root modules:
  - `config`: Pydantic settings, logging setup, neutral Django settings implementation.
  - `storage`: storage path and checksum helpers.
  - `metadata`: metadata matching and suggestion extraction utilities.
  - `rules`: rule-text placeholder/rendering helpers.
  - `operations`: operational workflows such as backup/restore.
- Place feature-specific core services under `services/<feature>/`.
  - Current service packages include `cards`, `card_groups`, `card_merges`, `catalog`, `decks`, `imports`, `parser_jobs`, and `templates`.
  - Service package `__init__.py` files expose the stable public API for that feature.
- Place feature-specific core repositories under `repositories/<feature>/`.
  - Current repository packages include `cards`, `card_groups`, `decks`, `exports`, `import_jobs`, `metadata`, and `templates`.
  - Shared repository helpers belong in `repositories/helpers.py`; avoid recreating legacy `*_repository.py` modules.
- Prefer importing from package public APIs, such as `card_reader_core.repositories.cards` or `card_reader_core.services.decks`, rather than deep module paths unless the caller is inside the same package.
- Keep shared frontend logic in `frontend/src/composables`.
  - Use domain subfolders such as `card-filters`, `card-gallery`, `decks`, `cards`, and `admin` when shared logic belongs to a real domain concept.
  - Shared card filtering logic belongs in `frontend/src/composables/card-filters`: route/query parsing, stable key-based filter state, key/id translation, API filter param building, lifecycle helpers, and filter controller composables.
  - Shared gallery/search behavior belongs in `frontend/src/composables/card-gallery` or root composables such as `useCardCollection`, `useGalleryOptions`, and preference composables.
  - Page modules such as gallery/review/pickers should only own page-specific behavior like pagination, navigation context, and scroll restoration.
- Keep shared Vue components in `frontend/src/components`.
  - Use domain subfolders such as `app`, `cards`, `decks`, `filters`, `forms`, and `modals`.
  - If a component is consumed by more than one module, move it to `frontend/src/components` instead of importing across module component folders.
- Keep frontend module roots focused on module entrypoints and core module files.
  - Acceptable module-root files are pages/views, `api.ts`, `types.ts`, stores, and other true module entrypoints.
  - Place module-owned implementation details under `components`, `composables`, `utils`, or `tests`.
  - Do not import from another module's `components`, `composables`, or `utils` folders; promote genuinely shared code to root `frontend/src/components` or `frontend/src/composables`.
- Django owns the domain schema through migrations in `services/core`.
- When adding, removing, or changing Django database models or relationships, update `docs/card-database-diagram.svg` when the card-related schema diagram is affected.
- SQLite is the default database. Do not introduce Postgres-only behavior without explicit approval.
- Import flow remains async:
  - API creates jobs and items.
  - Parser claims queued work.
  - Parser writes results through core repositories/services.
- Persist imported images under the configured storage root using hash-based filenames.
- Keep parser provider-agnostic. PaddleOCR is the default behind parser-owned adapter boundaries.
- Keep Vue API compatibility stable unless a requested change explicitly requires a contract change.
- Card sorting follows collection ownership:
  - paginated or query-backed card collections should sort in the backend
  - already-loaded embedded card collections may sort client-side for presentation
  - shared sort keys and semantics must stay aligned across both layers
- Card lifecycle status controls normal visibility:
  - `active` is the default for play/browsing surfaces such as gallery, grouped gallery, public group detail, catalog linked-card counts/previews, and exports.
  - `deprecated` cards should stay directly retrievable by id and available in explicit management/query flows such as `lifecycle_status=all` or `lifecycle_status=deprecated`.
  - Do not automatically remove deprecated cards from decks or groups; instead surface warnings/invalid public listing state where relevant.
  - Card group anchors must remain active. Deprecated non-anchor group members may remain in admin data, but should be hidden from active public group views.
  - When adding or consuming endpoints that return cards or card-derived counts, decide intentionally whether deprecated cards should be included and keep list/detail/count behavior consistent.
- Deck-building constraints are core-owned and exposed to clients through `GET /decks/rules`.
  - Card-level deck-building overrides live on `Card.deck_building_config_json`; hero cards use the same mechanism as future normal card-triggered constraints.
  - Supported rule ids are `mainboard_copy_limit`, `mainboard_card_count`, `mana_type_count`, `legendary_copy_limit`, and `sideboard_entry_quantity`.
  - Rules have `severity` values of `hard` or `soft`; hard violations affect deck validity, while soft violations only warn.
  - Rules have `scope` values of `mainboard` or `whole_deck`; scope defaults to `mainboard` unless a rule override changes it.
  - Hard rules can set `blocks_action`; action-blocking hard rules should prevent direct builder actions and API submissions that would exceed the rule.
  - Frontend code should consume `/decks/rules` for defaults and examples, keeping local fallback defaults only for load/error resilience.
- The card detail editor separates card-level and version-level edits:
  - `Card` tab owns Hero Card, Card Status, and Deck-Building Config.
  - `Card Version` tab owns parsed scalar fields, symbols, metadata groups, template selection, reset, and reparse actions.

## Auth Rules
- Auth is enabled by default.
- Card gallery and card assets are public.
- Import jobs, review, admin, catalog, templates, and exports require `is_staff=true`.
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
- Runtime storage is the repo-root `storage/` directory in development. The Python source package `card_reader_core/storage` is tracked; keep `.gitignore` scoped to `/storage/` for runtime data.

## Development Commands
From repo root:
- Install deps: `pnpm setup`
- Install Node deps only: `pnpm deps:js`
- Install Python deps only: `pnpm deps:py`
- Dev default: `pnpm dev`
- Dev all: `pnpm dev:all`
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

Local app URL:
- Use `http://localhost:8888` to reach the running web app in the local desktop environment.

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
  - prefer shared UI utilities over duplicating component-local styling; for custom scroll areas, use the shared `.app-scrollbar` utility in `frontend/src/styles.css`
  - prefer VueUse composables when they fit cleanly and reduce custom reactive glue
  - preserve and extend the shared light/dark theme system in `frontend/src/styles.css` and `frontend/src/composables/useTheme.ts`
  - prefer semantic theme primitives and token-backed shared classes over scattering raw light-only or dark-only color utilities across components
  - when adding or changing visible UI, verify both light and dark appearances instead of treating dark mode as optional follow-up polish

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
- `GET /decks/rules`
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
- Do not run service/integration tests

## Ad hoc commands
When running ad hoc checks in this repo, prefer the helper below so temporary
files, UV cache data, and pytest scratch paths stay inside `.tmp/codex/`:

```powershell
pwsh -ExecutionPolicy Bypass -File scripts/run-in-agent-env.ps1 -TaskName lint uv run --project . ruff check services/core/src
```
