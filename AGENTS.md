# AGENTS.md - Card Reader Monorepo

## Operating Rules
- Always read this file before working.
- Ask before editing `AGENTS.md`; update it when project guidance changes.
- Update `.gitignore` when adding generated, private, or machine-local files.
- Write scalable, readable code. Fix underlying issues cleanly instead of layering quick fixes.
- Never write absolute local filesystem paths into committed repository files or docs; use repo-relative paths instead.
- Run lint and typecheck before finishing tasks that touch related source, config, generated code, or typed contracts. For docs-only, diagram-only, or skill-only changes, validate the changed artifact directly instead.
- Codex reviews are triggered automatically by every commit pushed to a non-draft PR. Never request a Codex review manually or post `@codex review`. Track an active review through the original Codex PR comment/check, which is updated while reviewing. The absence of a newly submitted review does not mean no review is running. After pushing, wait for the automatic review to finish, then inspect and address any new threads.
- Before implementing a stateful workflow across browser and server mutations, define its authoritative success condition, idempotency boundary, independent failure domains, and cleanup semantics. Cleanup failures must never reverse or block an already confirmed authoritative success.

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
  - `notifications` owns durable user notification creation, event builders, coalescing policy, and future channel fanout seams.
  - Service package `__init__.py` files expose the stable public API for that feature.
- Place feature-specific core repositories under `repositories/<feature>/`.
  - Current repository packages include `cards`, `card_groups`, `decks`, `exports`, `import_jobs`, `metadata`, and `templates`.
  - `notifications` owns user notification persistence, unread counts, list queries, read-state updates, and coalescing writes.
  - Shared repository helpers belong in `repositories/helpers.py`; avoid recreating legacy `*_repository.py` modules.
- Prefer importing from package public APIs, such as `card_reader_core.repositories.cards` or `card_reader_core.services.decks`, rather than deep module paths unless the caller is inside the same package.
- The frontend uses four explicit layers under `frontend/src`:
  - `app`: bootstrap, router, shell, global orchestration, and global styles.
  - `features/<name>`: route and workflow slices. Keep private implementation details under the feature's `components`, `composables`, `utils`, and API files.
  - `domain/<name>`: reusable business contracts, API clients, state, UI, and logic consumed by multiple workflows.
  - `shared`: domain-agnostic API infrastructure, components, composables, router helpers, types, and utilities.
- Classify frontend code by ownership: app-wide orchestration belongs in `app`; business-specific code used by multiple workflows belongs in `domain`; business-specific code used by one workflow belongs in its `feature`; domain-agnostic reusable code belongs in `shared`.
- Frontend dependency directions are enforced by ESLint boundaries:
  - `app` may import app, features, domain, and shared.
  - `features` may import only the same feature, domain, and shared. Feature-to-feature imports are forbidden.
  - `domain` may import shared and only explicitly allowlisted domain slices. The allowlist in `frontend/eslint.config.js` is validated as an acyclic graph when ESLint loads; update it intentionally when adding a real cross-domain dependency.
  - `shared` may import shared only.
- Keep HTTP transport calls in focused `api.ts` or `api/*` clients owned by the relevant domain or feature. Components, pages, stores, and workflow composables consume those clients instead of calling the shared Axios instance directly.
- Use direct frontend file imports; do not add barrel or transitional re-export files solely to hide ownership.
- Co-locate frontend unit and component specs with their source. Reserve `tests/` directories for scenarios spanning several source files.
- Shared card queries, filters, gallery behavior, sorting, symbols, preferences, and reusable card UI belong in `frontend/src/domain/cards`.
- Shared deck contracts, clients, constraints, calculations, exports, route helpers, tags, and reusable deck UI belong in `frontend/src/domain/decks`; deck-building contracts live in `frontend/src/domain/deck-building` to keep card/deck ownership acyclic.
- Reusable auth/session, notification, template, card-back, review, and access-request contracts and state belong in their matching `frontend/src/domain` slices.
- Playtester is a frontend-only manual deck sandbox.
  - Deck selection lives at `/playtester` and should reuse existing deck list UI patterns, compact deck cards, summary deck records, and the shared playtest table/lower-bar surface; active play lives at `/playtester/:deckId`.
  - Treat `/playtester` and `/playtester/:deckId` as the playtester surface for route-scoped UI such as hotkey help and global-navigation hotkey suppression.
  - Deck selector search/listing may use existing deck summary endpoints, including query-backed summaries; fetch full deck detail only when card entries are needed for previewing or active play.
  - Active playtest state is local-storage backed per deck and `deck.updated_at`; avoid backend persistence unless explicitly requested.
  - Mainboard cards expand into physical `PlaytestCardInstance` copies in the shuffled library; sideboards stay reference-only.
  - The hero starts in the dedicated `hero` stack outside the library.
  - The flow starts in `opening`, where exact physical mana/setup copies can be reserved across mulligans, then transitions to `play` when the hand is kept.
  - The selector may build a read-only opening-hand preview from real playtest state and save that preview as the starting draft when starting a new playtest.
  - Board interactions use the custom pointer drag layer, right-click context menus, stacks, card-level visual piles, drag-box group selection, active play hotkeys, and hold-only middle-click zoom.
  - Playtester card scale is a local preference shared by the selector and active play surface; keep scale math in the playtester card-scale utility.
  - Reuse Playtester feature components such as `PlaytestTableSurface`, `PlaytestLowerBar`, `PlaytestStack`, and `PlaytestStackPopover` before duplicating hand, stack, or table-surface UI.
  - Keep Playtester implementation details under `frontend/src/features/playtester/components`, `utils`, or `composables`; reusable deck/card business code belongs in its domain slice and domain-agnostic helpers belong in shared.
  - Keep Playtester state responsibilities separated: initialization/normalization in `playtestStateCore.ts`, board mutations in `playtestBoardState.ts`, opening setup in `playtestOpeningState.ts`, and storage migration/serialization in `playtestDraftPersistence.ts`. Import the owning file directly.
- Django owns the domain schema through migrations in `services/core`.
- When adding, removing, or changing Django database models or relationships, update `docs/card-database-diagram.svg` when the card-related schema diagram is affected.
- When changing documented feature behavior, workflows, permissions, API contracts, onboarding, or operations, review the relevant guides under `docs/` and update them when they are no longer accurate. Also review `docs/README.md` when documentation is added, removed, or renamed.
- Card pool, role, and faction work has twelve approved, dependency-ordered implementation checkpoints. Execute them in order and keep each step independently reviewable and verified:
  1. `docs/card-classification-step-1-foundation.md`
  2. `docs/card-classification-step-1-1-authorization-seam.md`
  3. `docs/card-classification-step-2-import-inference.md`
  4. `docs/card-classification-step-2-1-pool-scoped-identity.md`
  5. `docs/card-classification-step-2-2-import-workflow-seam.md`
  6. `docs/card-classification-step-2-3-faction-classification.md`
  7. `docs/card-classification-step-3-card-pool-workspaces.md`
  8. `docs/card-classification-step-3-1-context-preserving-workspace-switching.md`
  9. `docs/card-classification-step-3-2-admin-owned-inference-rules.md`
  10. `docs/card-classification-step-4-filter-hardening.md`
  11. `docs/card-classification-step-4-1-pool-aware-gallery-filters.md`
  12. `docs/card-classification-step-4-2-pool-aware-filter-values.md`
- Deliver the classification feature through the umbrella branch `feature/card-classification`, with its aggregate PR targeting `master`. Each checkpoint uses a separate branch and PR targeting `feature/card-classification`; merge checkpoints into the umbrella branch in dependency order, and branch the next checkpoint from the updated umbrella branch. Keep the aggregate PR open for whole-feature CI and review, and do not retarget checkpoint PRs to `master` merely to trigger checks or reviews. Do not merge the umbrella PR to `master` until Steps 4.0 through 4.2 acceptance and the aggregate review are clear.
- The target card classification model has three independent card-level dimensions:
  - `card_pool` is exactly one of `player`, `evil`, or `neutral`; `game_master` is a temporary undeployed value removed by Step 2.1 and must not remain as a compatibility alias.
  - `card_roles` is a set of zero or more code-owned roles: `hero`, `boss`, `location`, `boon`, `event`, and `shop_item`; roles may coexist.
  - `card_factions` is a set of zero or more code-owned factions: `order`, `blood`, `dark`, and `metal`; factions may coexist.
  - Normal is the product label for the derived empty-role state and must not be persisted as a role. Keep `standard` only as the existing internal/query sentinel for that derived state.
  - Pool/role/faction conventions belong in core code, not mutually-exclusive or same-pool database constraints. Cross-pool relationships are allowed.
  - Pool, roles, and factions belong to the stable `Card` record; template remains version/parser configuration.
  - Stable human-readable card identity is scoped by pool plus the exact canonical faction set: normalized primary names, aliases, and untargeted image-hash matching must resolve inside one explicit `(card_pool, card_factions)` namespace. Same-name cards may coexist in different faction namespaces. Roles never participate in identity matching.
  - Faction assignments and the derived faction identity key form one invariant. Runtime faction mutations must go through the cards identity seam so assignments plus card and alias namespace keys update atomically.
  - Neutral remains a separate stable pool. Do not include it implicitly in Player or Evil queries; any future Neutral overlay must be an explicit, authorized multi-pool view state.
- Ordinary Gallery filter visibility is code-owned frontend presentation policy, not card validity, authorization, or import inference:
  - Hide the Roles facet in Player, Evil, and Neutral. Roles remain persisted code-owned classification for inference, overrides, manual editing, business logic, Admin, Review, and explicit API queries.
  - Show Factions only in Evil. Show Mana, including its mana-cost range, Affinity, and Devotion only in Player. All other Gallery facets retain their current visibility until another approved filter pass changes them.
  - Keep the facet matrix and sanitation in one cards-domain Gallery policy. Do not infer it from card data, result counts, Tags, Types, symbols, or classification rules, and do not add database/Admin/developer-data configuration for it.
  - Before loading Gallery results, remove every hidden facet's include, exclude, match-mode, and numeric state from the canonical route and request. Admin, Review, global maintenance, and purpose-specific Player deck filters must not inherit this Gallery-only policy.
- Ordinary Gallery filter value availability is a separate backend-derived concern:
  - For Keywords, Tags, and Types, an exact authorized `card_pool` request returns only values linked to the latest version of at least one active Card in that pool. It is independent of the Gallery's other active filters rather than a fully dynamic facet count.
  - Omitting `card_pool` preserves the complete authorized-scope catalog used by Admin, Review, maintenance, and other global consumers. An invalid pool is rejected, and an unauthorized restricted pool follows the centralized pool-access policy.
  - Gallery must discard stale cross-pool catalog responses and reconcile unavailable route selections so hidden values cannot remain as ghost filters. A failed catalog request must not be treated as a successful empty catalog or erase route state.
  - Keep the initial implementation query-backed and bounded, with query-count coverage and no cache, persistence, migration, or developer-data change. Measure before introducing caching, and leave Symbols, Mana, Templates, numeric ranges, Roles, Factions, and whole-facet visibility unchanged.
- The Player/Evil/Neutral workspace scopes ordinary browsing and workspace-owned card collections, not global staff operations. Admin and Review always use the staff user's complete authorized pool scope regardless of the selected shell workspace; their mixed-pool records, counts, queues, searches, suggestions, and previews must retain explicit pool labels where ambiguity is possible. Imports may consume the workspace only as a visible, editable default.
- Evil and Neutral card access must use the centralized backend card-pool scope whose initial policy is staff-only for both pools. Enforce it on direct objects, collections, embedded payloads, exports, and image/assets; frontend visibility is not the security boundary. Session/frontend code consumes ordered accessible pools rather than separate Evil and Neutral booleans. Keep the policy centralized so it can later expand without card-data migration.
- Until the twelve card-classification checkpoints are complete, preserve their boundaries: Step 1 owns schema/migration/manual editing/filtering and Hero replacement; Step 1.1 owns authorization-seam consolidation; Step 2 owns the initial role import inference and overrides; Step 2.1 owns the final Player/Evil/Neutral pool contract, pool-scoped name/alias/hash identity, and related authorization/session renaming; Step 2.2 owns upload admission and cleanup, grouped-reparse transactionality, import activity/detail refresh consistency, and explicit evidence-state contracts; Step 2.3 owns faction persistence, pool-plus-exact-faction natural identity, the completed role vocabulary, and generalized role/faction mechanics; Step 3 owns the global three-pool sidenav workspace and site-level scoping; Step 3.1 owns context-preserving workspace selection, centralized route capabilities, routed-component lifetime, and safe fallback only for incompatible routes; Step 3.2 removes template inference and hard-coded tag policies, adds admin-owned pool-specific Tag/Type inference rules, and snapshots those rules for deterministic jobs while keeping role/faction definitions code-owned; Step 4.0 owns the integrated classification acceptance and bounded cleanup audit without adding new filter persistence; Step 4.1 owns the code-owned pool-aware Gallery facet matrix, Roles removal from Gallery, and hidden route/request sanitation while preserving global management and backend filter capabilities; Step 4.2 owns exact-pool Keyword/Tag/Type availability from active Cards' latest versions, optional pool-scoped filter metadata, stale-response protection, catalog-backed ghost-filter reconciliation, and bounded query measurement while preserving omitted-pool global catalogs and deferring caching and fully dynamic faceting.
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
  - `default` is the canonical single-pool sort: Player orders by mana family, then Hero before the default role order, then ascending mana value; Evil orders by Order, Blood, Darkness, then no faction, followed by Boss, Location, the default role order, and ascending mana value; Neutral uses the default role order
  - the default role order is Normal, Hero, Boss, Location, Boon, Event, then Shop Item; pool-specific priority roles are moved ahead of that order without duplicating them
  - multi-valued factions and roles sort by their earliest effective value, then their complete effective membership vector; grouped Gallery results use their anchor Card's values
  - keep the pool sort as declarative mirrored component lists in backend and frontend code so future priority changes remain localized; query-backed defaults must translate those components to SQL annotations and paginate in the database
  - canonical mana-family order is Arcane, Dark, Divine, Martial, Occult, then Primal; changing it requires a release
  - paired mana and affinity symbols represent the same canonical family for family sorting, filtering, and deck-builder hero presets
  - query-backed mana-family sorting uses the indexed `CardVersion.mana_family_sort_key`; numeric colorless symbols and unmatched affinities stay in the no-family bucket
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
- Deck list surfaces that only need listing metadata should use summary deck records/endpoints and `DeckListRecord`-compatible shared components; fetch full `DeckRecord` only for detail, editor, export, or playtest flows that need full board entries.
- The card detail editor separates card-level and version-level edits:
  - The `Card` tab owns Card Pool, multi-valued Card Roles and Factions, Card Status, and Deck-Building Config; Normal and No faction are derived when their assignment sets are empty.
  - `Card Version` tab owns parsed scalar fields, symbols, metadata groups, template selection, reset, and reparse actions.
- User notifications are durable, core-owned in-app records.
  - `NotificationService` is the only public creation API; API views, frontend code, and feature call sites must not write notification rows directly.
  - Domain code should emit meaningful events through typed notification helpers; notification code owns recipient selection, copy, target URLs, metadata, dedupe keys, and channel fanout.
  - Stored in-app notifications are the source of truth. Future email, push, realtime, and digest delivery should dispatch after notification creation instead of branching inside cards, decks, parse flags, or other feature services.
  - Store rendered title/message snapshots plus structured metadata so old notifications remain readable and future channels can render richer payloads.
  - Noisy notification types must intentionally use stable dedupe keys or explicitly opt into one notification per event.

## Auth Rules
- Auth is enabled by default.
- Card gallery and card assets are public. Deck TTS exports follow deck visibility; gallery and
  content-version TTS exports require staff access.
- Player cards remain the public/default pool. Evil and Neutral cards and their direct details, embedded payloads, exports, and assets are staff-only until the centralized restricted-pool scope policy is deliberately expanded.
- Import jobs, review, admin, catalog, templates, and user-selected exports require `is_staff=true`.
- Maintenance endpoints require `is_superuser=true`.
- Developer-data metadata, browser downloads, and bootstrap-code creation require an active
  authenticated user who is either staff or has the Developer role. Code exchange is
  unauthenticated, but exchange and download-token authorization must re-check that the issuing
  user remains active and still has developer-data access. Bundle creation and build history are
  staff-only.
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

## Developer Data
- `dev-data/selection.json` owns the reviewed public selection keys and coverage requirements;
  `dev-data.lock.json` pins the immutable bundle version, format, SHA-256, and website API URL.
- Developer-data bundles may contain catalogs, templates, deck tags, symbol assets, the current card
  back, and curated cards with their versions, images, aliases, groups, metadata, content versions,
  lifecycle state, and deck-building overrides.
- Developer-data bundles do not contain TTS card-sheet rows, coordinates, or rendered atlases. After
  import, reconcile and render fresh local sheets from the imported Card images.
- Bundles must exclude users, decks, notifications, activity/access records, import jobs, uploads,
  raw OCR, parse flags, suggestions, logs, debug crops, credentials, and source/server paths.
- Production bundles live outside `maintenance/`, under `/var/lib/card-reader/dev-data` by default.
  Published versions are immutable and retained for older pinned branches.
- Django owns authorization and returns `X-Accel-Redirect` in production; Nginx owns transfer and
  ranges. Never expose the internal filesystem path or make the internal URI externally accessible.
- `publish_dev_data` is production-only and must validate through an isolated temporary import.
  Production startup must never import a developer bundle automatically.

## Docker And Runtime
- `api`, `parser`, and `developer-data-builder` share runtime data at `/var/lib/card-reader`.
- `tts-sheet-renderer` uses the API image, core polling-worker abstraction, shared database, and shared
  runtime storage. TTS sheet rows are the durable coalescing queue; no external broker is required.
- Persistent TTS sheet slots are append-only. Never move, compact, delete, or reuse a Card identity's
  assigned sheet coordinate; merges preserve source slots and resolve them to the target Card.
- Website TTS exports for decks, sideboards, gallery selections, and content versions all use the
  `card-reader.tts-cards.v2` persistent-sheet payload. The object importer spawns those sheets directly and must not
  depend on scripting regions, preloaded card libraries, name matching, or automatic library synchronization.
- TTS deck exports preserve saved quantities and order, mark hero/mainboard/sideboard roles, include deprecated
  Cards still referenced by decks, and require usable hero artwork for main-deck exports.
- The default `docker-compose.yml` preserves the deployment storage contract by bind-mounting the
  host paths selected by `CARD_READER_APP_DATA_DIR` and `CARD_READER_PUBLIC_APP_DATA_DIR`.
- Use `docker-compose.local.yml` when local Docker development should replace those bind mounts with
  the Docker-managed `card_reader_data` volume.
- The parser container defaults to `linux/amd64` because the locked PaddlePaddle release has no
  Linux ARM64 wheel. Docker Desktop provides emulation on Apple Silicon.
- Native full-workspace development supports Windows x86_64, Linux x86_64, and macOS ARM64 on
  Python 3.12 or 3.13; `.python-version` pins the default environment to Python 3.12.
- On unsupported non-x64 native hosts, preflight verifies the container fallback by running an
  `alpine:3.21` probe as `linux/amd64`; keep this aligned with the parser service platform.
- API container startup runs migrations, user seeds, default seeds, then Gunicorn.
- Parser container waits for the API health check and assumes the schema is ready.
- Parser container uses `DJANGO_SETTINGS_MODULE=card_reader_core.django_settings`.
- Runtime settings are provided through `CARD_READER_*` environment variables.
- Runtime storage is the repo-root `storage/` directory in development. The Python source package `card_reader_core/storage` is tracked; keep `.gitignore` scoped to `/storage/` for runtime data.

## Development Commands
From repo root:
- Install all dependencies: `pnpm setup:deps`
- Install Node deps only: `pnpm deps:js`
- Install Python deps only: `pnpm deps:py`
- Dev default: `pnpm dev`
- Dev all: `pnpm dev:all`
- Build all: `pnpm build`
- Lint all: `pnpm lint`
- Typecheck all: `pnpm typecheck`
- Test all: `pnpm test`
- Bootstrap a clean development checkout: `pnpm bootstrap:dev`
- Reset with a local safety backup and bootstrap: `pnpm bootstrap:dev:reset`

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
  - prefer shared UI utilities over duplicating component-local styling; for custom scroll areas, use the shared `.app-scrollbar` utility from `frontend/src/app/styles/utilities.css`
  - prefer VueUse composables when they fit cleanly and reduce custom reactive glue
  - preserve and extend the shared light/dark theme system in `frontend/src/app/styles/base.css`, `frontend/src/app/styles/components.css`, `frontend/src/app/styles/utilities.css`, and `frontend/src/shared/composables/useTheme.ts`; `frontend/src/app/styles.css` is the ordered Tailwind/import entrypoint
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
- `GET/HEAD /tts/card-sheets/{sheet_id}/image.webp`
- `POST /exports/tts/cards`
- `GET /decks/{deck_id}/exports/tts`
- `GET /symbols/assets/{asset_path}`
- `GET /exports/csv`
- `GET /decks/rules`
- `GET /notifications`
- `GET /notifications/summary`
- `PATCH /notifications/{notification_id}`
- `POST /notifications/mark-all-read`
- `GET /developer-data/current`
- `POST /developer-data/grants`
- `POST /developer-data/grants/exchange`
- `GET /developer-data/bundles/{version}/download`
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

```bash
uv run --no-project python scripts/run-in-agent-env.py --task-name lint -- uv run --project . ruff check services/core/src
```
