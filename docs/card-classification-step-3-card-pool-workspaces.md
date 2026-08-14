# Card Classification Step 3: Player, Evil, and Neutral Workspaces

Status: implemented.

Navigation amendment: [Step 3.1](card-classification-step-3-1-context-preserving-workspace-switching.md) replaces this step's initial unconditional safe-landing navigation with a centralized route-capability policy. Compatible global and resource routes stay mounted when the workspace changes; Gallery changes pool in place; only incompatible Player-only routes fall back to the target Gallery.

Filter-default amendment: [Step 4.1](card-classification-step-4-1-pool-aware-gallery-filters.md) removes the ordinary Gallery Roles facet and its former default Hero exclusion. Deck-building retains explicit purpose-owned Hero filtering.

This step turns the card pool into a site-level browsing context. It does not change the classification model or infer new data.

## Outcome

Add a primary Player/Evil/Neutral workspace selector to the sidenav. Player is the default workspace for everyone. Evil and Neutral are initially available only when the session's centralized card-pool scope permits restricted pools, whose initial backend policy is staff-only.

The active workspace scopes navigation and ordinary card collections to exactly one pool. Staff-only operational tools remain available in every permitted workspace. Admin and Review are global operational surfaces over every pool authorized for the staff user; the workspace picker must not silently filter their data. Direct cross-pool relationships remain allowed and render safely without changing a card's classification.

## Locked decisions

- The UI labels and stable data values are **Player** (`player`), **Evil** (`evil`), and **Neutral** (`neutral`). `game_master` is not a supported compatibility alias.
- Workspace state is navigation/query context, not card ownership and not authorization.
- Backend capabilities remain authoritative. Hiding the toggle is not a security boundary.
- Player is the default for new sessions, logged-out users, and users whose allowed pool scope contains only Player.
- Evil and Neutral share one restricted-pool access policy that initially maps to staff. Session/frontend code consumes the ordered allowed-pool scope rather than separate Evil and Neutral booleans.
- Ordinary card collections are hard-scoped to one pool. An `all pools` option is reserved for explicit staff management tools and must not become a normal workspace.
- Admin and Review are explicit global staff tools. Their catalogs, counts, queues, searches, linked-card payloads, suggestions, and previews use the viewer's full authorized pool scope and do not change when the shell workspace changes.
- Neutral is its own stable pool and is not included automatically in Player or Evil. A future product pass may add an explicit Neutral overlay to either workspace, but that must remain an authorized multi-pool query state rather than multiple card ownership or silent request expansion.
- Hero is excluded by default in each workspace. Boss, Location, Boon, Event, and Shop Item are not globally excluded. Faction filters have no default exclusions.
- Cross-pool links do not automatically change the active workspace. A linked Player Hero opened from an Evil or Neutral card is visibly labeled Player, while Back/return navigation preserves the originating workspace.
- Relationship management treats the relationship anchor/target pool and the member-search pool as separate concepts. Staff must be able to select any permitted pool for each member search without reclassifying the group, its anchor, or existing members.
- Relationship routes use the target or anchor pool supplied by the relationship payload. They must not infer that pool from the source card, the current workspace, or a stale selected-card version.
- Treat every deck supported by the current deck builder as a **Player deck**. A later deck-design project may add explicit pool classification to stable deck identities, but this workspace step must not infer that classification from a deck's cards or force Evil/Neutral material into the current hero/mainboard/sideboard model.
- Playtester remains Player-only. It is hidden from Evil and Neutral navigation and must accept only explicitly Player-classified decks once deck classification exists.
- A future **Scenario** is a higher-level composition, not a mixed-pool deck: it may group one or more Player decks with Evil and Neutral Boons, Events, Locations, and other scenario material. This step must preserve that direction without introducing a scenario schema prematurely.

## Authoritative success condition

The step succeeds when every normal card-derived collection request carries one explicit Player/Evil/Neutral pool, the sidenav and route state agree on the active workspace, unauthorized users cannot enter or retain Evil or Neutral workspaces, and backend tests/checks confirm that direct URLs and assets remain protected.

Local preference persistence is convenience only. The session's allowed pool scope and current route are authoritative for whether Evil or Neutral context may be used.

## Workspace state design

Add code-owned frontend pool types and labels under `frontend/src/domain/cards`. Own reusable pool query behavior with the card domain; keep shell placement and global route orchestration under `frontend/src/app`.

The workspace state contains:

- active pool: `player`, `evil`, or `neutral`;
- the ordered `accessible_card_pools` granted to the current session;
- the last permitted pool preference.

Persist the preference with the existing VueUse/local-storage conventions. On initialization:

1. Read the session's accessible pool list.
2. Read a valid route pool when the route supports pool context.
3. Otherwise use the last permitted preference.
4. Fall back to Player.

When authentication or capability changes remove the active Evil or Neutral pool, synchronously increment a session/workspace request generation, switch to Player, replace the disallowed route/query state, clear restricted cached collection data, and only then issue new requests. Logging out from a restricted context must never leave a flash of protected data.

Every asynchronous card-derived request captures the current generation, requested pool, session identity, and allowed-pool scope. Before committing data, errors, pagination, or loading state, it verifies that all captured values are still current and that the pool remains permitted. `AbortController` cancellation may reduce wasted work, but cancellation alone is not the boundary because a response can win the race. A late Evil or Neutral response after logout, staff removal, or session refresh is discarded and cannot repopulate a store or rendered view.

Use the existing route filter/query infrastructure. `card_pool` remains shareable in card-gallery URLs; direct card detail routes derive the card's actual pool after loading and preserve the caller's explicit return location.

## Sidenav and navigation

Update `frontend/src/app/components/AppShellNav.vue` with a prominent three-option control near the application identity and before primary navigation.

- All users see Player as the active context.
- Each Evil or Neutral option appears only when that pool is present in the session's allowed scope.
- Collapsed desktop navigation uses an accessible compact control or menu with an unambiguous tooltip/label.
- Mobile navigation exposes the same state and behavior.
- Switching workspaces closes the mobile drawer. After Step 3.1, compatible routes remain in place, Gallery changes pool in place, and only incompatible routes navigate to the target workspace's safe landing route.

Player workspace navigation initially contains:

- Gallery
- Decks
- Playtester
- My Decks when authenticated
- Build a deck when authenticated
- Notifications and Settings under their existing access rules

Evil and Neutral workspace navigation initially contains:

- Gallery
- Notifications and Settings under their existing access rules
- future pool-specific entries only when implemented

Decks, My Decks, Build a deck, and Playtester are intentionally absent from Evil and Neutral workspaces. Existing deck routes remain Player-workspace routes until a future deck classification model is designed.

Staff operational navigation such as Imports, Operations, Review Queue, and Admin stays separated below the existing divider and remains accessible from every permitted workspace. Imports should prefill their pool from the active workspace, while still displaying and requiring the pool field specified in Step 2.

Admin and Review remain global after navigation. The selected shell workspace may change navigation composition and Import defaults, but it must not filter Admin Catalog or Review data. These surfaces show every authorized pool together and retain visible pool badges or explicit pool fields wherever duplicate names or pool-specific configuration could otherwise be ambiguous.

## Collection and route scoping

Apply the active pool explicitly to every workspace-owned frontend request:

- gallery and grouped gallery;
- card search/select controls;
- card group views and embedded previews;
- exports initiated from a card collection;
- deck-builder hero and card galleries;
- Playtester deck/card preview surfaces;
- any workspace-owned card counts or suggestions.

Do not pass the active workspace as an implicit filter to Admin or Review. Their endpoints apply the centralized full card-pool scope for the staff user. Admin Catalog linked-card counts, suggestion occurrences, detail previews, and classification-rule records remain cross-pool; Review confidence cards, parse flags, queues, and summary counts remain cross-pool. Imports may consume the active workspace only as a visible, replaceable default.

Player deck, deck-builder, and Playtester requests always send `card_pool=player`, even if a staff user has Evil or Neutral as the shell workspace. If those routes are reached directly, keep their Player classification explicit and show the Player workspace or route back to a safe restricted-pool page according to the route guard. Once decks have their own explicit pool, Playtester must reject or omit every non-Player deck independently of the cards currently embedded in it.

On a workspace switch, increment the request generation and discard the outgoing collection result before fetching the incoming pool. Every response must pass the generation/pool/scope guard before it may mutate state. Do not show stale cards under another pool's heading.

Gallery defaults in each pool:

- active cards;
- current workspace pool;
- Hero excluded;
- other role filters empty.
- faction include and exclude filters empty.

Switching pool resets transient gallery filters to these defaults for the target pool in the first implementation. Preserve pagination, selection, and export state only when it is valid for the target pool; otherwise clear it explicitly. Do not carry an implicit Neutral overlay between workspaces because that overlay is not part of this checkpoint.

## Backend capability and authorization audit

Step 1 introduces the central capability and baseline protection. This step must perform a complete audit rather than assuming the navigation is sufficient.

Verify the central `card_pool_scope_for_user` authorization seam is used by:

- card list/grouped list queries;
- card detail, version, generation, and image endpoints;
- immutable image asset resolution;
- groups and embedded card payloads;
- catalog counts/previews;
- exports and TTS surfaces;
- deck validation and public deck serialization;
- notifications or activity payloads that embed card details;
- developer-data download/import policy, which remains Player-only.

Expose the ordered `accessible_card_pools` session contract introduced in Step 2.1. The frontend consumes that scope and does not infer it from `is_staff`, even though staff is the initial restricted-pool policy.

If the future policy changes, the intended edit points are the backend capability policy, session payload, and access-control documentation—not card rows, pool values, or gallery logic.

## Cross-pool relationships

Do not add a generic same-pool restriction. Evil or Neutral Boons, Events, and Locations may intentionally link to Player Heroes or cards in another restricted pool.

For any existing or future relationship serializer:

- authorize the target card independently;
- include the target's `card_pool`, `card_roles`, and `card_factions`;
- include the relationship anchor/target pool needed to construct a direct route without borrowing the source card's pool;
- display a pool badge when the target differs from the active workspace;
- preserve the originating return route/workspace;
- never expose an unauthorized Evil or Neutral target through a Player/public relationship payload.

For staff relationship editors and selectors:

- expose an explicit search-pool control for each lookup operation;
- allow members from any permitted pool regardless of the existing anchor pool;
- discard stale lookup results when the search pool changes;
- preserve each member's pool in the editor payload so changing the anchor updates the relationship's route pool correctly;
- refresh or reconcile relationship summaries after a card changes pool so stale chips cannot construct an invalid route.

This step does not create a new link model. It establishes behavior for relationships that already exist or are added later.

## Deferred deck and scenario model

The current deck domain is Player-focused. Its Hero, mainboard, sideboard, validation, export, and Playtester assumptions must not be treated as the definition of a future Evil or Neutral deck.

When deck classification is designed later:

- classify the stable deck identity explicitly instead of deriving its pool from contained cards;
- keep Player deck validation limited to Player-pool cards;
- define any Evil or Neutral deck structure and validation deliberately before exposing those routes;
- keep Playtester limited to Player decks unless a separate restricted-pool testing workflow is designed;
- model scenarios above decks and cards/groups so a scenario can reference Player decks together with Evil and Neutral Boons, Events, Locations, and future scenario material without weakening ordinary deck pool rules.

The deck field name, migration, Evil/Neutral deck contents, scenario cardinalities, ownership, visibility, and authoring UI are all deferred. Step 3 only reserves the navigation and scoping boundaries needed to avoid coupling them to the Player deck implementation.

## Frontend ownership

- Card pool contracts, request parameters, labels, and reusable preference helpers belong in `frontend/src/domain/cards`.
- Sidenav rendering, global route synchronization, auth-transition handling, and workspace-aware nav composition belong in `frontend/src/app`.
- Gallery filter state continues to use the existing card filter utilities.
- Import prefill remains in `frontend/src/features/import-jobs` and consumes the domain/app workspace contract without importing another feature.
- Do not create feature-to-feature imports or a second pool state owned by Imports, Gallery, or Decks.

All visible changes must use semantic theme primitives and be verified in light and dark modes.

## Implementation sequence

1. Confirm Step 1 capability enforcement, Step 2 explicit import classification, Step 2.1 pool-scoped identity, Step 2.2 workflow seams, and Step 2.3 faction classification are complete.
2. Add the frontend card-pool workspace/preference contract and tests.
3. Consume the ordered session pool-scope contract.
4. Add desktop, collapsed, and mobile sidenav controls.
5. Make nav item composition workspace-aware.
6. Synchronize workspace, route query, auth changes, and initial safe landing routes; Step 3.1 refines voluntary switching to preserve compatible routes.
7. Scope gallery and all reusable card collection clients.
8. Keep existing deck routes Player-scoped, hide them and Playtester from Evil/Neutral navigation, and lock Playtester to Player decks explicitly.
9. Prefill, but do not hide, the import pool from the active workspace.
10. Audit all backend card-derived payloads and assets for capability enforcement.
11. Update current-state card, import, access, deck, and Playtester documentation.
12. Run all permitted validation and manually verify both themes and responsive nav modes.

## Required tests

Add or update tests covering:

- Player default with no stored preference;
- permitted Evil and Neutral preference restoration;
- invalid/disallowed stored values falling back to Player;
- logout, staff removal, or session refresh while Evil or Neutral is active;
- deferred Evil and Neutral responses resolving after access loss and being rejected before they can mutate data, errors, pagination, or loading state;
- desktop, collapsed, and mobile toggle behavior;
- workspace-specific nav item composition;
- safe landing routes and route-query synchronization, followed by Step 3.1 coverage for context-preserving compatible routes;
- clearing stale collections during a switch and rejecting responses from the previous request generation;
- gallery Hero-excluded defaults in all three pools;
- every workspace-owned collection request carrying an explicit pool;
- Admin and Review requests remaining global across the staff user's authorized pools regardless of the selected workspace;
- deck builder and Playtester remaining Player-scoped;
- import pool prefill without removing explicit confirmation;
- direct cross-pool links preserving the originating workspace;
- relationship links using the target/anchor pool instead of the source card or workspace pool;
- staff adding members from any permitted pool to an existing relationship and changing the anchor across pools;
- stale relationship summaries being removed or refreshed after a card pool edit;
- unauthorized Evil and Neutral list requests returning `403`;
- unauthorized Evil and Neutral object/image access returning `404`;
- staff access to all corresponding surfaces.
- no ordinary workspace request implicitly including Neutral;
- explicit cross-pool relationships remaining visible only when every embedded target is authorized.

Do not run prohibited service/integration suites. Run affected permitted frontend tests, lint and typecheck for touched packages, Django checks, and manual browser verification at `http://localhost:8888` when the local app is available.

## Acceptance criteria

- Player/Evil/Neutral is the primary sidenav context on desktop and mobile.
- Evil and Neutral options are visible only when present in the session's allowed pool scope.
- Player is the safe default and automatic fallback after access loss.
- In-flight Evil or Neutral responses cannot repopulate frontend state after the session loses access.
- Normal galleries never mix pools.
- Neutral is never included implicitly in Player or Evil; any future overlay remains an explicit, separately authorized state.
- Hero is excluded by default in all three workspaces.
- Player deck building and Playtester never admit Evil or Neutral cards.
- Imports visibly prefill the current workspace while retaining explicit pool confirmation.
- Staff tools remain reachable from every permitted workspace.
- Admin Catalog and Review retain the same authorized all-pools data when the shell workspace changes.
- Direct cross-pool relationships render with pool context and no unauthorized data leak.
- Staff relationship editors can add and anchor cards across pools without an implicit same-pool restriction.
- Changing the future Evil/Neutral access audience requires a centralized scope-policy change, not data migration.
- Light/dark, expanded/collapsed desktop, and mobile navigation are verified.
- Lint, typecheck, Django checks, affected permitted tests, and documentation validation pass.

## Explicit non-goals

- Deck classification, Evil/Neutral deck structure/building, scenario persistence, or restricted-pool Playtester behavior.
- New Evil- or Neutral-specific tools beyond the scoped Gallery.
- A new card-to-card relationship model.
- Public or ordinary authenticated Evil/Neutral access in the initial release.
- An ordinary mixed-pool gallery.
- Neutral overlays in Player or Evil; the first implementation keeps all three workspaces strictly separate.
- Automatic workspace changes when following cross-pool links.
