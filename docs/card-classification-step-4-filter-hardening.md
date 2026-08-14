# Card Classification Step 4.0: Classification Acceptance Audit and Cleanup

Status: planned.

Steps 1 through 3.2 established the Player/Evil/Neutral pool model, multi-valued roles and factions, pool-plus-faction identity, deterministic import classification, restricted-pool authorization, workspace navigation, and admin-owned inference rules. Step 4.0 treats those contracts as one completed feature and validates them as an integrated product surface before the classification umbrella can merge.

This checkpoint is deliberately an audit and cleanup pass. Pool-aware Gallery filter presentation is now owned by Step 4.1. Step 4.0 must not add the superseded role-filter visibility model, Admin configuration, API metadata, migration, or developer-data Version 6 contract from the earlier draft.

## Outcome

After this checkpoint:

- the classification feature has an explicit backend, API, frontend, migration, authorization, import, identity, and developer-data acceptance matrix;
- defects and proven duplication discovered by that audit are fixed within the approved classification architecture;
- stale compatibility paths and documentation from intermediate checkpoints are removed or amended;
- larger findings are recorded as bounded follow-up checkpoints instead of expanding this audit without approval;
- the umbrella branch passes its permitted CI suites and automatic review with the complete classification feature present.

## Locked decisions

- Step 4.0 does not create filter-visibility persistence or an Admin filter-visibility editor.
- Gallery no longer needs role-by-pool option visibility. Step 4.1 removes the Roles facet from ordinary Gallery browsing while retaining roles as code-owned, persisted classification used by inference and business logic.
- Pool-aware Factions, Mana, Affinity, and Devotion facet presentation and hidden-filter route cleanup belong exclusively to Step 4.1.
- Roles and factions remain assignable in the Card editor, targetable by import overrides and inference rules, visible in Admin/Review management surfaces, and queryable through their existing API parameters.
- Admin and Review remain global staff workflows and must not inherit Gallery workspace filtering.
- This audit may consolidate demonstrably duplicated seams, but it must not introduce new gameplay concepts, role/faction validity constraints, Neutral overlays, deck/scenario behavior, or access-policy changes.

## Authoritative success condition

The audit succeeds when the matrices below are represented by stable automated tests, all discovered in-scope defects are fixed, larger findings are documented with a proposed owner/checkpoint, current-state documentation matches behavior, and the classification branch passes its full permitted CI and automatic review.

Individual test, lint, documentation, or UI failures remain independent findings. Fix the owning seam rather than adding compatibility branches or suppressing the failure.

## Classification acceptance audit

Prefer parameterized pool/role/faction matrices and shared fixtures over copying one test per value or endpoint.

### Canonical registries and persistence

- Player, Evil, and Neutral keys, labels, ranks, validation, and frontend formatting agree.
- Hero, Boss, Location, Boon, Event, and Shop Item keys, labels, ranks, normalization, and frontend formatting agree.
- Order, Blood, and Darkness keys, labels, ranks, normalization, and frontend formatting agree.
- Normal remains the derived empty-role product label; `standard` remains only the internal empty-role query sentinel.
- Role and faction assignments remain independently multi-valued and reject duplicate rows without adding pool-validity constraints.
- The faction assignment set and derived faction identity key stay synchronized through supported mutation paths.
- Migration forward and reverse guards remain accurate for the final undeployed schema.

### Stable identity and manual editing

- Primary names, aliases, and untargeted image hashes resolve inside the exact `(card_pool, card_factions)` namespace.
- Same-name and same-art cards can coexist across pools and exact faction sets.
- Rename, pool move, faction move, alias preservation, destination conflict, rollback, and concurrent edits use the centralized card identity seam.
- Cross-pool and cross-faction merges remain rejected while valid same-namespace merges preserve aliases and relationships.
- Manual pool, role, and faction edits preserve ids, versions, groups, decks, redirects, and unrelated assignments.

### Import classification and lifecycle

- Automatic Tag/Type rule matching is selected by pool and can independently assign multiple roles and factions.
- Exact role and faction overrides bypass their corresponding automatic dimension without coupling the two dimensions.
- New jobs snapshot the complete applicable rule set; queued jobs remain deterministic after live rules change.
- Grouped reparses, live-versus-queued evidence, and resolved-empty classification states retain the Step 2.2 transaction and evidence contracts.
- Same-name and same-image imports resolve only within the exact pool/faction identity namespace.
- Same-identity role differences preserve authoritative live roles and produce warnings; faction differences create separate natural identities.
- Upload admission, authoritative job creation, cancellation, cleanup, parser success, and post-success hooks retain their independent success boundaries.

### Authorization and workspace boundaries

- Anonymous and ordinary users receive Player-only card scope; staff receive Player, Evil, and Neutral in canonical order.
- Restricted collection requests return `403`; direct restricted cards, versions, images, assets, exports, and embedded identities remain `404` to unauthorized viewers.
- Session scope loss invalidates cached and mounted restricted resources without relying on frontend visibility as the boundary.
- Gallery and other workspace-owned card collections remain single-pool and never add an implicit Neutral overlay.
- Admin and Review retain the complete authorized scope regardless of the selected shell workspace.
- Player-only deck builder and Playtester routes remain unavailable outside Player without defining Evil deck or scenario behavior.

### API and frontend contracts

- `/auth/me`, login responses, `/cards/filters`, card payloads, import payloads, and edit payloads use only the final pool/role/faction vocabulary.
- Route capability and workspace switching keep compatible routes mounted and use Gallery fallback only for incompatible routes.
- Pool labels remain explicit on mixed-pool global staff surfaces.
- Frontend canonical registries are consumed consistently without introducing feature-to-feature imports or parallel labels.
- Current Gallery role and faction filtering remains covered until Step 4.1 intentionally changes the ordinary Gallery surface.

### Admin, Review, and developer data

- classification-rule management is global, pool-explicit, deterministic, and validated against code-owned role/faction definitions;
- Admin Catalog role/faction usage and linked-card previews retain explicit pool context;
- Review queues, counts, suggestions, and previews remain global over authorized pools;
- the current developer-data format round-trips the final pools, roles, factions, aliases, identity namespaces, classification rules, and coverage contract;
- public card selection remains Player-only and does not accidentally resolve same-key Evil or Neutral twins;
- generated locks remain tool-owned and are never hand-edited.

## Cleanup audit

Inspect and remove only demonstrably obsolete or duplicated classification behavior:

- temporary Game Master literals or compatibility aliases outside historical migrations;
- template inference hints and hard-coded pre-Step-3 classification policies;
- direct staff checks that bypass the centralized card-pool authorization seam;
- unscoped card key, alias key, or image-hash lookup paths;
- duplicated frontend pool, role, faction labels or normalization outside their canonical registries;
- role/faction mutation paths that bypass the identity or classification service owning their invariant;
- stale tests, fixtures, and docs that present an intermediate checkpoint as current behavior.

Do not perform unrelated formatting churn or speculative framework extraction. If a finding requires a public contract change outside the accepted classification architecture, document it as a proposed Step 4.x rather than implementing it here.

## Current-state documentation after implementation

Review and update, where behavior changed:

- `docs/card-management.md`;
- `docs/imports.md` and related import workflow guidance;
- `docs/access-control.md`;
- `docs/developer-data.md`;
- `docs/card-database-diagram.svg` if an in-scope schema correction is required;
- `docs/README.md`.

Retain Steps 1 through 3.2 as the incremental design record. Add amendment notes only where an earlier plan's current-state statement is superseded.

## Implementation sequence

1. Start `feature/card-classification-step-4-acceptance-audit` from the updated `feature/card-classification` umbrella branch.
2. Commit the approved Step 4.0/4.1 planning and any separately approved `AGENTS.md` guidance before implementation.
3. Build shared parameterized fixtures and the acceptance matrices without changing behavior merely to make tests easier.
4. Run the matrix in focused groups, cluster failures by owning seam, and fix root causes in reviewable commits.
5. Perform the bounded duplication and stale-compatibility audit, removing only code proven obsolete by the final contracts.
6. Update current-state documentation after behavior and tests are stable.
7. Run permitted validation, open a non-draft PR targeting `feature/card-classification`, and nurture CI and automatic Codex review until clear.
8. Do not merge without the user's direction. Branch Step 4.1 only from the umbrella after Step 4.0 is merged there.

## Validation

Run:

```text
pnpm --filter @card-reader/core lint
pnpm --filter @card-reader/core typecheck
pnpm --filter @card-reader/api lint
pnpm --filter @card-reader/api typecheck
pnpm --filter @card-reader/parser lint
pnpm --filter @card-reader/parser typecheck
pnpm --filter @card-reader/web lint
pnpm --filter @card-reader/web typecheck
pnpm --filter @card-reader/web test -- <affected classification, workspace, import, and admin specs>
uv run --project ../.. --package card-reader-api python manage.py check
uv run --project ../.. --package card-reader-api python manage.py makemigrations --check --dry-run
```

Validate SVG XML if the diagram changes. Do not run prohibited local service or integration suites; place required cross-service coverage in CI. Verify any visible fixes in light and dark themes at desktop and mobile widths.

## Acceptance criteria

- The final pool, role, faction, identity, inference, authorization, workspace, and developer-data contracts are covered by the integrated matrices.
- Every discovered in-scope defect is fixed at its owning seam.
- Obsolete intermediate compatibility code is removed without weakening historical migration safety.
- Admin and Review remain global; ordinary workspaces remain explicitly single-pool.
- No role-filter visibility model, API, migration, Admin editor, or developer-data Version 6 change is introduced.
- Broader findings are documented as separately approved follow-up work.
- Current-state docs match the verified implementation.
- Lint, typecheck, Django checks, migration drift, targeted frontend tests, CI suites, and automatic review are clean.

## Explicit non-goals

- Implementing the Step 4.1 Gallery facet policy.
- Inferring filter availability from card counts, assignments, metadata, or inference rules.
- Adding pool/role or pool/faction validity constraints.
- Making canonical pools, roles, or factions admin-creatable.
- Adding roles, factions, pools, or an implicit Neutral overlay.
- Redesigning decks, scenarios, Evil deck behavior, or Playtester.
- Changing staff-only Evil/Neutral authorization.
