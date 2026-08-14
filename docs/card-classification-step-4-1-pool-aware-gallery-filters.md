# Card Classification Step 4.1: Pool-Aware Gallery Filter Surfaces

Status: implemented, validated, reviewed, and merged into the classification umbrella branch.

Step 4.1 is a deliberately small frontend-only change that makes the ordinary Card Gallery's filter surface match the active Player, Evil, or Neutral workspace. It removes the Roles facet from Gallery browsing and hides pool-irrelevant Factions, Mana, Affinity, and Devotion facets without changing their backend data, query capabilities, classification behavior, or global staff-management use.

This is presentation and route-state policy, not authorization or card validity. Values for hidden facets must be reset before the Gallery request so invisible constraints can never affect results. Removing the Roles facet also removes the former code-owned Hero exclusion from ordinary Gallery defaults; deck-building workflows continue applying their purpose-specific Hero rules explicitly.

## Implementation record

- `GALLERY_VISIBLE_FILTER_SECTIONS` is the single readonly Player/Evil/Neutral matrix in the cards domain.
- `sanitizeGalleryFilterStateForPool` resets hidden semantic groups before canonical route replacement and before the existing key-to-selection-to-request conversion path.
- `CardFilterSections` now controls Roles and Factions independently while retaining its complete default surface for global Admin and maintenance consumers.
- Gallery route reconciliation watches the actual route as well as its sanitized signature, replaces incompatible direct or historical URLs before fetching, and uses sanitized state for results, CSV, TTS, summaries, and reset behavior.
- No backend, API, persistence, Admin configuration, developer-data, or database-diagram contract changed.

## Outcome

After this checkpoint:

- the ordinary Gallery shows only facets meaningful to its active pool;
- Roles are no longer exposed as a Gallery browsing filter in any pool;
- switching pools or opening an incompatible saved URL removes hidden facet values before fetching cards;
- roles remain elevated backend classification for inference, overrides, manual editing, business logic, Admin, Review, and explicit API queries;
- the shared filter UI remains usable by global Admin and Player-only deck-building consumers without accidentally inheriting Gallery-only policy;
- future Evil mana support requires one deliberate policy change rather than scattered template conditions.

## Locked facet matrix

The initial ordinary Gallery visibility matrix is:

| Gallery facet | Player | Evil | Neutral |
| --- | --- | --- | --- |
| Roles | Hidden | Hidden | Hidden |
| Factions | Hidden | Shown | Hidden |
| Mana | Shown | Hidden | Hidden |
| Affinity | Shown | Hidden | Hidden |
| Devotion | Shown | Hidden | Hidden |

All other existing Gallery facets retain their current visibility until a later filter pass explicitly changes them.

“Mana” includes the complete existing Mana section: canonical mana-family/symbol include and exclude selections, match mode, and minimum/maximum mana cost. Evil does not expose that section until Evil mana symbols and their intended semantics exist.

## Locked decisions

- Remove the Roles facet only from ordinary Gallery browsing. Do not remove `CardRoleAssignment`, canonical role registries, import inference/overrides, Card editor controls, Admin Catalog badges and management, Review information, repository filters, API query parameters, exports, or developer-data role coverage.
- Normal disappears with the Gallery Roles facet. It remains the product label for the derived empty-role state and `standard` remains the supported internal/API empty-role query sentinel.
- Factions are shown only in the Evil Gallery. This is not a constraint against unusual faction assignments in Player or Neutral.
- Mana, Affinity, and Devotion are shown only in Player. Their backend filters remain valid and unchanged.
- The facet matrix is code-owned frontend presentation policy under `frontend/src/domain/cards`. Do not add database rows, migrations, Admin configuration, `/cards/filters` applicability metadata, or developer-data format changes for it.
- Admin and Review remain global across all authorized pools and must not consume the selected workspace's Gallery facet policy.
- The maintenance filtered-reparse surface remains a global staff filter consumer. It keeps the complete filter surface and explicit pool selection unless a separate maintenance plan changes it.
- Deck builder and Playtester remain Player-only. Their purpose-specific visible-section choices remain independently owned; Step 4.1 must not broaden or narrow those workflows accidentally.
- API validation remains based on supported filter values, not whether the ordinary Gallery currently displays a facet.
- Do not infer facet visibility from result counts, card assignments, symbols present in a pool, Tags, Types, inference rules, or other mutable data.
- Keep the implementation intentionally mechanical: one readonly pool-to-visible-section table, one Gallery sanitation helper, and the minimum rendering split needed to control Roles and Factions independently.
- Changing the policy later must require editing the central table and its matrix test, not a migration, Admin operation, API response, or component rewrite.
- Do not create a generalized filter-policy framework, new composable, new store, additional API layer, or alternate filter-state model for this checkpoint.

## Authoritative behavior

For every ordinary Gallery transition, the effective filter state is the route state sanitized against the active pool's facet policy. Only that sanitized state may be serialized back to the canonical Gallery URL or translated into a card API request.

When a user switches pools, follows a direct URL, uses browser history, or restores stale saved state:

1. parse and normalize the route using the existing card-filter utilities;
2. apply the active workspace pool;
3. reset every field owned by a hidden facet to its canonical default;
4. replace a non-canonical URL before issuing the next card request;
5. build selection ids and the API payload from the sanitized state only;
6. prevent a stale request created before sanitation from replacing current results.

Values removed while leaving a pool are not silently retained for later restoration. Returning to that pool starts those facets at their normal defaults unless the current canonical route explicitly supplies valid values.

## Minimal frontend ownership

Add one small cards-domain module, for example `frontend/src/domain/cards/utils/filters/cardGalleryFacetPolicy.ts`, containing:

- a typed readonly `GALLERY_VISIBLE_FILTER_SECTIONS` table keyed by Player, Evil, and Neutral;
- a selector that returns the table entry for a pool;
- `sanitizeGalleryFilterStateForPool(state, cardPool)`, implemented with the existing normalized state shape and existing defaults.

That is the entire new policy seam. Do not mirror it in API metadata or distribute pool checks through components.

Make the minimum change to `CardFilterSections` needed to control Roles and Factions independently. Replace the coarse combined `classification` visibility decision with granular `roles` and `factions` section keys while keeping the existing component, state adapter, event API, markup components, and default-all behavior for callers that do not supply `visibleSections`. Do not redesign the shared filter component.

`CardGalleryPage` passes the selected pool's section list and sanitizes its state through the helper. Keep generic normalization in `cardFilterState.ts`, route serialization in `cardFilterRouteState.ts`, catalog/id translation in `cardFilterSelection.ts`, and transport mapping in `cardFilterRequest.ts` unchanged unless a tiny call-site adaptation is strictly required. Admin, maintenance, and deck consumers continue calling the same shared component as today.

## Hidden field groups

Sanitation must clear the whole semantic group, including match controls that otherwise look inactive:

- Roles: included roles, excluded roles, and role match mode.
- Factions: included factions, excluded factions, and faction match mode.
- Mana: mana-family/symbol includes, excludes, match mode, mana-cost minimum, and mana-cost maximum.
- Affinity: affinity includes, excludes, and match mode.
- Devotion: devotion includes, excludes, and match mode.

Clear key-based Gallery route state before the existing conversion path builds id-based selection and request state. Do not add a second sanitizer for API payloads: sanitized Gallery state flowing through the existing conversion path is the single guarantee.

## Route and request contracts

- Direct Gallery URLs containing role parameters normalize those parameters out in every pool.
- Faction parameters survive only in Evil Gallery routes and requests.
- Mana-family/symbol and mana-cost parameters survive only in Player Gallery routes and requests.
- Affinity and Devotion parameters survive only in Player Gallery routes and requests.
- Pool switching replaces the existing Gallery route in place and does not add history entries solely for sanitation.
- Unrelated filters, search, sort, display preferences, and pagination behavior retain their existing semantics.
- Explicit calls to `GET /cards` and global management consumers may still use every supported role/faction/symbol/cost filter in any authorized pool.
- Gallery CSV/TTS exports use the same sanitized effective filter payload as visible Gallery results.

## UI behavior

- Do not render empty wrappers or unexplained spacing where the classification section previously appeared.
- Preserve the current order of all remaining facets.
- Evil places Factions in the natural classification position before its other filters.
- Player begins with Mana after the Gallery search/header because Roles and Factions are absent.
- Neutral begins with the first currently shared facet after classification; it must not show empty Roles, Factions, Mana, Affinity, or Devotion panels.
- Active-filter summaries, reset behavior, and result counts must reflect only the sanitized state.
- Verify desktop/mobile layouts and light/dark themes for all three pools.

## Testing

### Policy unit tests

- exact visible facet matrix for Player, Evil, and Neutral;
- Roles absent for every pool;
- every hidden facet field resets to the canonical default;
- visible facet values remain unchanged;
- sanitation is deterministic and idempotent;
- adding Evil to Mana later is represented by one registry change and covered by the matrix fixture.

### Route and request tests

- direct URLs with hidden role/faction/mana/affinity/devotion parameters normalize before the first request;
- Player-to-Evil, Evil-to-Neutral, Neutral-to-Player, browser-back, and browser-forward transitions remove only newly hidden fields;
- no hidden role value reaches `buildCardFilterApiPayload` for Gallery requests or exports;
- visible Evil faction and Player mana/affinity/devotion parameters survive round trips;
- removed match-mode parameters return to defaults;
- stale pre-switch responses cannot replace the new pool's results.

### Component and workflow tests

- Gallery renders the exact facet matrix in each pool at desktop and mobile layouts;
- no empty classification container remains in Player or Neutral;
- global maintenance/Admin filter surfaces retain their complete filters;
- Deck Builder's Player-only and hero-step section policy remains unchanged;
- Reset clears all effective Gallery filters and cannot reintroduce hidden state;
- CSV/TTS Gallery exports match the currently displayed result constraints.

### Unchanged backend contract

No backend implementation or contract test changes are expected. Existing CI remains the regression guard for role, faction, mana, affinity, and devotion query support. If implementation appears to require a backend change, stop and reassess the frontend seam rather than expanding Step 4.1.

## Documentation after implementation

Update current-state Gallery/filter guidance to describe the pool-specific facet matrix and explain that roles are management/inference classification rather than an ordinary browsing facet. Amend Step 4.0 only where implementation findings change its audit record. No database-diagram or developer-data update is expected because Step 4.1 adds no persistence.

## Implementation sequence

1. Merge the completed Step 4.0 checkpoint into `feature/card-classification` and branch `feature/card-classification-step-4-1-pool-aware-gallery-filters` from that umbrella head.
2. Commit the approved Step 4.1 plan and any separately approved `AGENTS.md` guidance before implementation.
3. Add the readonly Gallery section matrix, the single state sanitizer, and their focused tests in the cards domain.
4. Make the minimal Roles/Factions visibility split in `CardFilterSections` without changing its existing state/event contract or default global behavior.
5. Apply the matrix and sanitizer at the Gallery route/state boundary so existing requests, active summaries, reset behavior, and exports consume the already-clean state.
6. Add focused transition, route, component, export, and unchanged-consumer coverage.
7. Verify all three pools visually in desktop/mobile and light/dark modes, then update current-state docs.
8. Run permitted validation, open a non-draft PR targeting `feature/card-classification`, and nurture CI and automatic Codex review until clear. Do not merge without the user's direction.

## Validation

Run:

```text
pnpm --filter @card-reader/web lint
pnpm --filter @card-reader/web typecheck
pnpm --filter @card-reader/web test -- <affected card filter, route, Gallery, deck, and Admin specs>
```

The normal PR pipeline still validates the untouched backend. Do not run prohibited local service or integration suites. No Django check, migration drift, or SVG validation is needed because Step 4.1 must not touch backend models or schema; if it does, the implementation has exceeded the plan.

## Acceptance criteria

- Roles are absent from the ordinary Gallery in Player, Evil, and Neutral.
- Factions appear only in Evil Gallery.
- Mana, including mana cost, appears only in Player Gallery.
- Affinity and Devotion appear only in Player Gallery.
- Every hidden facet value is reset before canonical Gallery routes, requests, exports, active-filter summaries, and result loading.
- Returning to a pool does not resurrect values removed when they became hidden.
- Admin, Review, maintenance, Card editing, imports, and explicit API queries retain complete role/classification capabilities.
- Deck Builder and Playtester retain their existing Player-only behavior.
- The policy is changed by editing one readonly pool-to-section table and its matrix test.
- The sanitation logic has one Gallery-owned cards-domain helper with no payload-specific duplicate.
- Generic card filter state, request, catalog, and API contracts are not redesigned.
- No persistence, migration, Admin configuration, developer-data format change, or API schema change is added.
- Light/dark, desktop/mobile, lint, typecheck, targeted tests, CI, and automatic review are clean.

## Explicit non-goals

- Removing roles from the domain model or management workflows.
- Constraining which roles, factions, or symbols may be assigned to cards in a pool.
- Making filter facet visibility configurable in Admin.
- Inferring visible facets from present card data or result counts.
- Adding Evil mana symbols or enabling Mana in Evil.
- Redesigning all remaining filter options or adding count-aware facets.
- Changing global Admin/Review scope, authorization, Neutral overlays, decks, scenarios, or Playtester.
