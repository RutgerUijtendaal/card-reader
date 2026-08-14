# Card Classification Step 4.2: Pool-Aware Gallery Filter Values

Status: implemented and locally validated on the checkpoint branch; pull-request review pending.

Implementation record:

- `GET /cards/filters` accepts an optional exact `card_pool`; omitted requests preserve the complete legacy catalog, while explicit requests authorize one pool and availability-scope Keywords, Tags, and Types.
- Keyword and Tag availability use indexed `EXISTS` subqueries; Types retain pool-relative linked-card counts and omit zero-linked rows for exact-pool requests. The measured core service remains fixed at four metadata queries with thirty linked cards and options.
- Gallery binds filter hydration to both workspace generation and requested pool, discards stale results, and keeps the prior catalog unavailable during transitions.
- Successful catalogs reconcile Keyword, Tag, Type include, and Type exclude route keys through the cards-domain selection seam. Failed catalogs preserve route state, keep card browsing usable, disable catalog-dependent exports, and expose a read-only retry.
- No cache, persistence, migration, developer-data, database-diagram, Symbol, role, faction, or facet-visibility contract changed.

Step 4.1 decides which filter sections the ordinary Gallery displays in each Player, Evil, or Neutral workspace. Step 4.2 makes the values inside the currently shared Keyword, Tag, and Type sections relevant to that workspace: a pool-scoped Gallery response includes only values linked to at least one active card's latest version in the selected pool.

This is pool-scoped option availability, not fully dynamic faceted search. A Tag remains available when it occurs anywhere in the selected pool even if the user's other active filters would currently reduce that Tag to zero results. Facet visibility remains the frontend code-owned Step 4.1 policy; mutable card data controls only the values inside a visible facet.

## Outcome

After this checkpoint:

- Player, Evil, and Neutral Gallery workspaces hydrate distinct Keyword, Tag, and Type option sets from the backend;
- switching workspaces cannot leave an unavailable metadata key silently constraining Gallery results;
- global Admin, Review, maintenance, and other existing consumers retain their complete authorized metadata catalog unless they explicitly request one pool;
- authorization is checked before any restricted-pool facet response is returned;
- the endpoint continues using a small, bounded number of indexed database queries;
- no server cache, persistent browser cache, invalidation registry, materialized facet table, migration, or developer-data contract is introduced.

## Locked decisions

- Step 4.2 initially scopes only Keywords, Tags, and Types. Symbols, mana families, templates, numeric ranges, roles, factions, and other filters retain their existing value contracts until a later explicit extension.
- Availability means linked to the latest version of at least one active card in the exact selected pool.
- Availability depends only on pool and the locked active/latest-card rule. It does not depend on search text, other metadata selections, role/faction filters, numeric filters, pagination, sort, or the current result count.
- Deprecated-only metadata values are not offered by the ordinary pool-scoped Gallery catalog. Global management consumers retain the complete catalog. Lifecycle-aware Gallery faceting is deferred rather than making lifecycle an implicit cache/query dimension in this checkpoint.
- The Step 4.1 facet matrix remains code-owned frontend presentation policy. Data-derived availability must not make whole sections appear or disappear.
- Roles remain absent from ordinary Gallery filters. This checkpoint does not restore them or infer role availability.
- `GET /cards/filters` without a pool preserves its current authorized-scope behavior for global consumers.
- `GET /cards/filters?card_pool=<pool>` returns an exact single-pool catalog after authorization.
- Player remains public. Explicit unauthorized Evil or Neutral filter-catalog requests return the established generic restricted-pool `403`; they must not fall back to Player or reveal whether a value exists.
- Do not cache the pool-specific response initially. Measure the real endpoint before accepting invalidation complexity.
- Do not combine unrelated metadata models into a bespoke SQL union or load every matching CardVersion merely to reduce the visible query count.
- No schema or database-diagram change is expected.

## Authoritative success and failure boundaries

The authoritative success condition for facet hydration is one successfully validated response for the current workspace generation and requested pool. Only that response may replace the current filter catalog or be used to remove unavailable route values.

Pool selection, facet hydration, route reconciliation, and card-list loading remain separate failure domains:

- a stale response from a previous workspace generation is discarded;
- a failed facet request does not become a valid empty catalog and must not erase route selections;
- a facet failure must not permanently block card browsing or replace a successful card-list result;
- retrying facet hydration is read-only and idempotent;
- successful current-pool hydration reconciles metadata keys before the next canonical request derived from that catalog;
- route replacement failure does not mutate the backend and remains independently retryable through normal navigation.

## Backend design

### API contract

Extend the existing endpoint with one optional query parameter:

```text
GET /cards/filters?card_pool=player|evil|neutral
```

Use a focused serializer for filter-metadata scope rather than reusing the complete card-list filter serializer.

- Omitted `card_pool`: retain the current response over the caller's complete authorized `CardPoolScope`.
- Present `card_pool`: validate the final three-value pool vocabulary, verify the caller's centralized scope allows it, then call core with an exact one-pool `CardPoolScope`.
- Obsolete or unknown values, including `game_master`, return `400`.
- Explicit inaccessible Evil or Neutral values return `403` with the existing restricted-pool collection copy.
- The response shape remains backward compatible. No new top-level facet schema or version field is required.

Gallery is the first consumer that supplies `card_pool`. Admin, Review, maintenance, deck tooling, and other existing consumers remain unchanged unless their own product behavior explicitly calls for exact-pool values later.

### Core facet context

Keep `get_filter_metadata` core-owned and continue passing a `CardPoolScope`. An exact pool is represented by a one-value scope rather than by adding Gallery concepts to repositories. The service owns which facets use availability-aware loaders; the API owns query validation and authorization.

Do not create one universal facet registry. Metadata lists, symbols, mana-family definitions, numeric ranges, and code-owned classifications have different result shapes. The reusable seam is the explicit card scope and shared active/latest relationship predicate, while each facet loader remains understandable and typed.

### Repository queries

Add pool/scope-aware availability loaders for Keywords and Tags. Extend the existing Type loader so exact-pool responses omit zero-linked Types while preserving its current pool-relative linked-card ordering and optional `linked_card_count` payload behavior.

Keyword and Tag availability should use indexed semi-join/`EXISTS` semantics unless measurement shows the existing annotated-count pattern is clearer without a meaningful penalty:

```text
metadata value exists
where a relationship points to
an is_latest CardVersion whose Card is active and in the requested scope
```

Ordering remains:

- Keywords: label order;
- Tags: label order;
- Types: linked-card count descending within the requested scope, then label/id tie-breakers, matching the current Type sorting contract.

Symbols remain on their current complete-catalog loader in Step 4.2. The response therefore keeps approximately the existing bounded query shape: one query per persisted metadata family, not one query per option or Card.

Reuse the same active/latest predicate across the three availability loaders. Do not duplicate subtly different lifecycle or pool joins.

## Frontend design

### Pool-explicit hydration

Extend `fetchCardFilters` to accept an optional exact `CardPool`. `CardGalleryPage` passes `workspace.activePool`; global consumers continue omitting it.

Keep request-generation protection in `useCardFilterController`. Associate every load with both its generation and requested pool so a late Player response can never populate an Evil or Neutral Gallery after a rapid workspace change.

Do not introduce localStorage, IndexedDB, a Pinia cache, or module-global response cache in this checkpoint. Each Gallery mount and workspace transition may issue one filter-metadata request.

### Reconcile unavailable selections

Step 4.1 removes values belonging to hidden sections synchronously. Step 4.2 adds a second, catalog-backed reconciliation for visible metadata sections after successful hydration.

Given the successfully loaded pool catalog:

- remove Keyword keys absent from `filters.keywords`; reset Keyword match mode when no Keyword selection remains;
- remove Tag keys absent from `filters.tags`; reset Tag match mode when no Tag selection remains;
- remove Type include and exclude keys absent from `filters.types`; reset Type match mode when neither side remains;
- preserve every still-available key and every filter dimension not owned by this checkpoint;
- make reconciliation deterministic and idempotent;
- replace a non-canonical Gallery URL rather than adding a history entry;
- build Gallery cards, CSV, TTS, summaries, and active-filter state only from the reconciled route state.

Never reconcile against `EMPTY_FILTERS` or a failed response. Empty arrays are authoritative only when returned successfully for the requested pool.

The implementation should extend the existing cards-domain filter sanitation/catalog seams instead of placing key pruning in `CardGalleryPage` conditionals. Generic normalized filter state stays in `cardFilterState.ts`, route serialization stays in `cardFilterRouteState.ts`, catalog translation stays in `cardFilterSelection.ts`, and request mapping stays in `cardFilterRequest.ts`.

### Loading and failure behavior

On a workspace transition, mark the previous catalog unavailable immediately and start the exact-pool request. A current-generation successful response becomes authoritative, reconciles the route, and enables the pool's filter values.

If hydration fails:

- preserve the parsed/canonical Step 4.1 route rather than deleting metadata selections;
- retain or show the existing filter-loading error/retry behavior;
- allow the card collection to remain independently usable rather than turning auxiliary metadata failure into a permanent Gallery outage;
- do not reuse another pool's catalog as a visual fallback.

Avoid duplicate card requests where practical. When the route contains pool-sensitive Keyword, Tag, or Type keys, the first authoritative request after successful hydration must use reconciled state. Requests or responses from before the current workspace generation remain unable to replace current results through the existing generation guards.

## Query and cache policy

Step 4.2 deliberately ships without a server or persistent client cache.

The current endpoint already evaluates separate Keyword, Tag, Symbol, and Type querysets. Pool availability changes the predicates on existing facet queries; it does not create a query per option. Add a regression test or query-capture assertion demonstrating a bounded query count for a seeded pool with many cards and repeated metadata links.

Record endpoint/query measurements during implementation and in PR validation. Caching becomes a separate approved optimization only when measurements show the endpoint is materially contributing to latency or database load.

If later justified, prefer this order:

1. session-memory, per-pool frontend cache with in-flight request coalescing and a short TTL;
2. stale-while-revalidate behavior keyed by session generation, pool, and any future explicit facet context;
3. short server TTL only after authorization and only with bounded staleness accepted;
4. a durable per-pool revision or materialized facet-presence index only at scale where exact invalidation is worth owning.

Any future client cache must clear on logout/session replacement so restricted facet metadata cannot survive a capability change. Exact server-cache invalidation would have to cover imports, latest-version promotion, manual metadata edits, pool moves, lifecycle changes, merges, catalog edits, developer-data import, and bootstrap operations; Step 4.2 must not partially implement that list.

## Testing

### Core and repository

- Keyword, Tag, and Type values linked only to another pool are absent from an exact-pool response.
- Values linked to Player/Evil/Neutral cards appear only in the corresponding exact-pool catalogs.
- A value shared by several pools appears in each applicable catalog once.
- Only latest CardVersion relationships contribute.
- Deprecated-card-only relationships do not contribute to an exact-pool Gallery catalog.
- Duplicate relationships across cards do not duplicate options.
- Keyword/Tag label ordering and pool-relative Type ordering remain deterministic.
- Global authorized-scope loaders retain their current complete-catalog behavior.
- Seeded high-cardinality coverage proves query count remains bounded and does not scale with option or Card count.

### API and authorization

- public omitted-pool and explicit Player responses remain available;
- staff can request exact Player, Evil, and Neutral catalogs;
- ordinary users receive `403` for explicit Evil/Neutral requests;
- invalid and obsolete pool values return `400`;
- omitted-pool staff responses retain global authorized metadata;
- response keys and option payloads remain backward compatible;
- each exact-pool response includes only its valid Keyword, Tag, and Type values while leaving Symbols and code-owned metadata unchanged.

### Frontend domain

- `fetchCardFilters` serializes an exact pool only when supplied;
- Gallery supplies the active workspace pool while global consumers omit it;
- stale cross-pool responses are discarded;
- successful catalog reconciliation removes unavailable Keyword, Tag, Type include, and Type exclude keys;
- match modes reset only when their complete selection group becomes empty;
- valid and unrelated filters survive reconciliation;
- reconciliation is deterministic and idempotent;
- a failed request preserves route selections and is not treated as an empty successful catalog.

### Gallery workflow

- direct URLs containing another pool's metadata keys canonicalize after successful facet hydration;
- Player-to-Evil, Evil-to-Neutral, and Neutral-to-Player switches show the correct values and remove unavailable active constraints;
- browser back/forward cannot restore a ghost metadata constraint for the wrong pool;
- pre-switch filter and card responses cannot replace current workspace state;
- Gallery card results, active-filter summaries, CSV, and TTS consume the same reconciled state;
- Admin, Review, maintenance, and deck consumers retain their existing global or workflow-specific catalog behavior.

## Documentation after implementation

Update current-state Gallery/filter documentation to explain that section visibility is code-owned while Keyword, Tag, and Type values are derived from active/latest Cards in the selected pool. Amend Step 4.1 only if implementation changes its recorded current-state behavior. No developer-data or database-diagram update is expected.

## Implementation sequence

1. Merge all preceding work into `feature/card-classification` and branch `feature/card-classification-step-4-2-pool-aware-filter-values` from that umbrella head.
2. Commit this approved plan and any separately approved `AGENTS.md` guidance before implementation.
3. Add exact-scope repository loaders and shared active/latest predicates with query-count and pool matrices.
4. Add the optional API pool parameter, centralized authorization, backward-compatible global default, and endpoint tests.
5. Extend the cards-domain filter client/controller with pool-explicit hydration and stale-response protection.
6. Add catalog-backed route reconciliation at the existing Gallery sanitation boundary, including failure semantics and export/request consistency.
7. Verify global Admin/Review/maintenance and Player-only deck consumers remain unchanged.
8. Measure the endpoint without caching, update current-state docs, and run permitted validation.
9. Open a non-draft PR targeting `feature/card-classification`, nurture CI and automatic Codex review until clear, and do not merge without the user's direction.

## Validation

Run:

```text
pnpm --filter @card-reader/core lint
pnpm --filter @card-reader/core typecheck
pnpm --filter @card-reader/api lint
pnpm --filter @card-reader/api typecheck
pnpm --filter @card-reader/web lint
pnpm --filter @card-reader/web typecheck
pnpm --filter @card-reader/web test -- <affected filter controller, route, Gallery, Admin, maintenance, and deck specs>
uv run --project ../.. --package card-reader-api python manage.py check
uv run --project ../.. --package card-reader-api python manage.py makemigrations --check --dry-run
```

Run focused core/API tests for facet queries, query count, authorization, and response contracts. Do not run prohibited local service or integration suites. Verify Player, Evil, and Neutral Gallery filters in light/dark themes at desktop and mobile widths.

## Acceptance criteria

- Gallery requests Keyword, Tag, and Type values for its exact active workspace pool.
- Every returned value is linked to at least one active Card's latest version in that pool.
- Other selected filters do not change the available option set.
- Unavailable metadata keys cannot remain as invisible Gallery request, export, summary, or route constraints after successful hydration.
- Failed or stale facet requests cannot erase valid state or populate the wrong workspace.
- Omitted-pool global consumers retain their current authorized-scope behavior.
- Restricted-pool authorization is enforced before metadata is returned.
- Query count is bounded independently of Card and option count.
- No cache, cache revision, invalidation hooks, persistence, migration, developer-data format, or database diagram change is added.
- Current-state docs, lint, typecheck, targeted tests, Django checks, migration drift, CI, and automatic review are clean.

## Explicit non-goals

- Fully dynamic facets based on every active filter or current result set.
- Displaying linked-card counts for new facets unless already part of the existing Type contract.
- Pool-aware Symbol, mana-family, template, numeric-range, role, or faction values.
- Lifecycle-aware or deprecated-only Gallery facet catalogs.
- Inferring whole-facet visibility from data.
- Caching, materialized facet tables, background facet rebuilds, Redis, or a new infrastructure dependency.
- Restoring the Gallery Roles filter or changing the Step 4.1 section matrix.
- Changing metadata assignment validity, import inference, card identity, authorization policy, Neutral overlays, decks, scenarios, or Playtester.
