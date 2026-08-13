# Card Classification Step 3.1: Context-Preserving Workspace Switching

Status: planned. Begin only after Step 3 is merged into the classification umbrella branch.

This checkpoint refines the Step 3 Player/Evil/Neutral picker so it changes the site's active card-pool context without unnecessarily sending the user back to Gallery. It does not change card classification, authorization, or the set of routes available in each workspace.

## Outcome

Treat a workspace selection as a context change first and a navigation decision second.

- Global and operational pages such as Settings, Imports, Operations, Review, Admin, and Notifications remain on their current route.
- Gallery remains Gallery and replaces its pool-scoped query state with the selected workspace's defaults.
- Cross-pool-capable card and group detail routes keep the currently opened object while their surrounding workspace and return context change.
- Player-only deck and Playtester routes cannot remain active in Evil or Neutral and therefore navigate to the selected workspace's Gallery.
- Failed or cancelled navigation never leaves the route and workspace store describing different contexts.

The result should match the user's mental model: the picker changes which part of the game they are working in, while the router intervenes only when the current route cannot operate in that workspace.

## Locked decisions

- Keep Player, Evil, and Neutral as the same three single-pool workspaces introduced in Step 3.
- Keep `accessible_card_pools` and the centralized backend pool scope authoritative. Step 3.1 changes navigation behavior, not access policy.
- Define workspace compatibility once in app-owned route metadata and one selection coordinator. Components must not maintain their own route-name allowlists.
- A route that is compatible with every accessible workspace stays mounted during a pool change. Switching context must not erase an in-progress Settings or staff workflow merely because the workspace generation changed.
- Gallery is pool-scoped and represents its workspace in the URL. Selecting Player keeps the canonical clean `/cards` URL; Evil and Neutral use explicit `card_pool` query values.
- Gallery switching resets pool-sensitive filters, pagination, selection, and export state to the target workspace defaults established by Step 3. It does not carry an implicit Neutral overlay.
- Card and card-group details are cross-pool-capable resource routes. Keep the current object open when the workspace changes, retain its visible actual-pool classification, and update workspace-owned Back/return context to the selected workspace.
- Card editing remains on the current card for staff. The selected workspace does not reclassify the card and must not overwrite unsaved editor state.
- Decks, My Decks, deck editing/building, and Playtester remain Player-only. Selecting Evil or Neutral from one of those routes uses that pool's Gallery as the safe fallback.
- Selecting Player while already on a Player-only route stays on that route.
- Authentication and authorization redirects remain higher priority than context preservation. Losing restricted-pool access still falls back synchronously to Player and clears restricted state as required by Step 3.
- The mobile drawer closes after a successful selection even when the route itself does not change.

## Authoritative success condition

A workspace selection is successful when the active pool, persisted permitted preference, route representation, navigation composition, and card-request generation all describe the selected pool, while the current route is preserved whenever its declared workspace capability allows it.

For routes that require fallback navigation or query replacement, navigation acceptance is the commit boundary: do not mutate the active workspace until the router accepts the destination. A cancelled or rejected route transition leaves the previous route, active pool, preference, and request generation unchanged.

For a compatible route that needs no URL mutation, selecting the pool commits directly through the workspace store. It still increments the workspace generation exactly once so stale card-derived responses are rejected, but it must not recreate the routed page component.

## Route capability model

Extend Vue Router metadata with one explicit, typed workspace behavior. Use names that fit the implementation, but preserve these four semantics:

| Capability | Routes | Selection behavior |
| --- | --- | --- |
| `global` | Settings, Notifications, Imports, Operations, Review, Admin, and authentication/setup routes where the picker can appear | Keep the same path and query; change only workspace context. |
| `gallery` | Card Gallery | Replace the Gallery route with the selected pool and its canonical default filter state. |
| `resource` | Public card detail, staff card editor, and card-group detail | Keep the same resource id and non-workspace route state; replace only workspace-owned return context. |
| `player-only` | Deck lists/details/editors/builders and Playtester | Stay in place for Player; selecting Evil or Neutral navigates to that pool's Gallery. |

Do not infer capability from URL prefixes inside the picker. Every routed surface must either declare a capability or receive one deliberate default enforced by a test. Prefer an explicit exhaustive route table so a newly added route cannot silently acquire unsafe switching behavior.

Redirect-only aliases such as `/` and `/import-jobs` inherit behavior from their resolved destination and do not need an independent user-visible transition.

## Central selection coordinator

Replace the switcher's direct `buildWorkspaceSelectionLocation` call with an app-owned coordinator that receives the current route and requested pool, reads the route capability, and returns or executes one typed selection decision:

- `stay`: no router navigation; commit the pool directly;
- `replace-gallery`: navigate to canonical target Gallery state, then commit;
- `update-resource-context`: replace workspace-owned return context without changing the resource identity, then commit;
- `fallback-gallery`: navigate away from an incompatible route, then commit;
- `reject`: inaccessible pool or rejected navigation; do not commit.

Keep destination calculation pure and unit-testable. Keep router execution and store mutation in the app layer. The cards domain continues to own pool types, labels, preference state, canonical Gallery pool serialization, and request-generation state; it must not import app routes or Vue components.

Coalesce repeated clicks while a route-changing selection is pending. A late completion from an older selection must not overwrite a newer accepted selection. The coordinator should capture a monotonically increasing selection attempt or otherwise guarantee last-intent-wins without committing an unaccepted route.

## Routed component lifetime

Step 3 currently includes `workspace.generation` in the global `RouterView` key, which recreates every routed page on every pool change. Remove that global coupling.

- Route identity continues to control normal component creation.
- Global/resource pages remain mounted during a context-only workspace selection.
- Gallery and other card-derived surfaces react explicitly to workspace or route state and invalidate their own requests.
- Existing generation, pool, session, and allowed-scope checks remain the boundary against stale responses; component destruction is not a security or consistency mechanism.
- Any card-derived state that previously relied on the global remount must gain an explicit watcher/reset or guarded request before the generation suffix is removed.

Audit preserved pages for pool-sensitive state. Context-independent form state, open tabs, scroll position, and unsaved edits stay intact. Pool-derived lookups, previews, counts, and suggestions refresh or clear under their owning composable without resetting the whole page.

## Route-specific behavior

### Global and staff workflows

Settings, Notifications, Imports, Operations, Review, and Admin keep their path, query, and component instance.

- Navigation items recompute immediately for the selected workspace.
- Imports may use the new workspace as the default for a pristine classification form, but must not overwrite an explicitly edited pool, a sealed upload attempt, recovered state, or an existing job filter.
- Review/Admin card searches and previews must issue their next pool-sensitive lookup with an explicit pool and discard stale results, while unrelated page controls remain intact.
- A global route must not add `card_pool` to its URL merely to persist the workspace; the permitted preference is the context source there.

### Gallery

Gallery selection remains a route transition because its URL is shareable and its collection is pool-owned.

- Player canonicalizes to `/cards` with no `card_pool` query.
- Evil and Neutral serialize their explicit pool.
- Switching resets filters to active cards, the selected pool, Hero excluded, empty other-role filters, and empty faction filters.
- Clear pagination, selection, pending export state, cached outgoing results, and old navigation continuation before the incoming request can render.
- Preserve no stale query value that is invalid or misleading in the target pool.

### Card and group resources

Card ids and group ids remain globally stable and independently authorized, so the selected workspace need not match the opened resource's pool.

- Keep the resource route and loaded object mounted.
- Continue showing its actual pool, roles, and factions; never relabel it as belonging to the selected workspace.
- Rewrite or clear only the app-owned Back/return target so subsequent return navigation enters the selected workspace rather than a stale originating Gallery.
- Preserve unrelated route state and editor tabs.
- Any related-card lookup remains explicitly pool-scoped and refreshes only when its owning UI says the active workspace controls that lookup.

### Player-only routes

The route metadata used by the existing Player guards becomes the source for incompatibility decisions.

- Player selection is a context-only no-op when Player is already active.
- Evil or Neutral selection resolves that workspace's canonical Gallery destination.
- Await route acceptance before committing the pool. A dirty-form or other leave guard that rejects navigation keeps Player active and leaves the form untouched.
- Direct navigation to a Player-only route continues to select/show Player according to Step 3; Step 3.1 does not expose those tools in restricted workspaces.

## Authentication and access changes

Preserve Step 3's stricter access-loss path independently from voluntary switching.

- Logout, staff removal, or session refresh that removes Evil/Neutral access immediately selects Player, invalidates restricted requests, clears restricted cached data, and replaces a disallowed route when necessary.
- A stale route-change or workspace-selection promise cannot restore a pool that is no longer accessible.
- Direct unauthorized restricted objects/assets retain existing `404` behavior, and unauthorized restricted collections retain their generic `403` behavior.
- No backend contract or database migration is required for Step 3.1.

## Frontend ownership

- `frontend/src/app/router` owns typed route capabilities, destination resolution, guards, and route-level tests.
- `frontend/src/app` owns the selection coordinator, `RouterView` lifetime, mobile drawer completion, and shell orchestration.
- `frontend/src/domain/cards` continues to own card-pool values, Gallery pool serialization, preference state, and request generations.
- Individual features own the smallest explicit reaction needed for their pool-derived data. Do not introduce feature-to-feature imports.
- The workspace switcher remains a presentation component and delegates decisions; it must not accumulate route tables or feature-specific branching.

## Implementation sequence

1. Merge the completed Step 3 checkpoint into `feature/card-classification`.
2. Create `feature/card-classification-step-3-1-context-preserving-workspace-switching` from the updated umbrella branch and open its PR against `feature/card-classification`.
3. Add typed, exhaustive workspace capability metadata to app routes and pure decision tests.
4. Introduce the centralized selection coordinator with accepted-navigation commit semantics and repeated-click race protection.
5. Update the switcher and mobile drawer to consume the coordinator.
6. Remove workspace generation from the global `RouterView` key.
7. Audit every preserved route for card-derived state that relied on remounting; add explicit reset/watch and stale-response guards where required.
8. Implement canonical Gallery switching and target defaults without regressing Player URL normalization.
9. Implement resource-route return-context replacement while preserving ids, loaded resources, editor tabs, and unsaved state.
10. Implement Player-only safe fallback behavior and rejected-navigation rollback.
11. Revalidate access-loss handling separately from voluntary switching.
12. Update current-state navigation/card/import/access documentation after behavior exists.
13. Run targeted and full permitted frontend validation, then verify expanded/collapsed/mobile behavior in light and dark themes.

## Required tests

Add or update tests covering:

- every route declaring or deliberately inheriting one workspace capability;
- Settings, Notifications, Imports, Operations, Review, and Admin retaining their route and component instance across all permitted pool selections;
- preserved local form/tab state on a global route;
- pristine Import pool defaults following context while edited, sealed, recovered, and job-filter state is preserved;
- Gallery switching between every Player/Evil/Neutral pair with canonical URLs and target defaults;
- selecting Player from Evil/Neutral Gallery without restoring the previous restricted preference;
- stale Gallery data, errors, pagination, selection, and exports being rejected or cleared;
- card detail, card editor, and group detail retaining the same resource and actual-pool badge while updating Back/return context;
- unsaved card editor state surviving a context-only switch;
- Decks, My Decks, deck editing/building, and Playtester staying put for Player and falling back for Evil/Neutral;
- a rejected Player-only route leave preserving the old route, pool, preference, and generation;
- repeated rapid selections committing only the latest accepted intent;
- mobile drawer closing after both context-only and navigated successful selections, but not treating rejection as success;
- route components no longer remounting solely because workspace generation changes;
- every preserved page's pool-derived request carrying the selected pool and rejecting stale generations;
- logout/access loss winning races against pending selections and never restoring restricted state;
- navigation composition updating immediately without route replacement;
- no implicit Neutral overlay or mixed-pool ordinary collection.

Do not run prohibited service/integration suites. Run affected frontend unit/component tests, the full permitted frontend suite, frontend lint and typecheck, and build because router metadata and the app entrypoint change. Run Django checks only if backend code is touched. Verify the visible switcher and transitions in light/dark, expanded/collapsed desktop, and mobile layouts.

## Acceptance criteria

- Switching workspace on a compatible global or operational page keeps the user on that page and preserves its non-pool local state.
- Gallery switches pool in place with canonical shareable URLs and clean target defaults.
- Card/group resource routes keep the current object and accurately show its real classification while their surrounding return context changes.
- Player-only routes fall back only when the selected workspace is incompatible.
- Rejected or superseded navigation cannot partially commit workspace state.
- Workspace changes no longer recreate every routed component.
- Pool-derived data refreshes explicitly and cannot leak stale restricted results.
- Access loss remains stricter than voluntary switching and always returns to an authorized state.
- The switcher contains no feature route allowlist; one typed route-capability policy owns the behavior.
- Player/Evil/Neutral authorization, classification, identity, and single-pool collection contracts remain unchanged.
- Required tests, lint, typecheck, build, documentation checks, and visible theme/responsive verification pass.

## Explicit non-goals

- Adding Evil/Neutral deck builders, restricted-pool Playtester behavior, scenarios, or deck classification.
- Neutral overlays or mixed-pool ordinary galleries.
- Changing which users can access Evil or Neutral.
- Reclassifying cards when workspace context changes.
- Persisting workspace context in the database or adding `card_pool` to every global URL.
- Redesigning page-specific filters beyond the resets required for a safe workspace switch.
