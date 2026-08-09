# Card Classification Step 3: Player and Game Master Workspaces

Status: approved implementation plan; blocked on [Step 1](card-classification-step-1-foundation.md) and [Step 2](card-classification-step-2-import-inference.md).

This step turns the card pool into a site-level browsing context. It does not change the classification model or infer new data.

## Outcome

Add a primary Player/Game Master toggle to the sidenav. Player is the default workspace for everyone. The Game Master workspace is initially available only to users with the named Game Master card capability, whose initial backend policy is staff-only.

The active workspace scopes navigation and card collections so Player and Game Master cards do not mix during ordinary use. Staff-only operational tools remain available in both workspaces. Direct cross-pool relationships remain allowed and render safely without changing a card's classification.

## Locked decisions

- The UI labels are **Player** and **Game Master**. Use the game's own future branded term only through a deliberate copy change; keep the stable data value `game_master`.
- Workspace state is navigation/query context, not card ownership and not authorization.
- Backend capabilities remain authoritative. Hiding the toggle is not a security boundary.
- Player is the default for new sessions, logged-out users, and users without Game Master capability.
- Game Master capability initially maps to staff, but the policy is centralized so it can later map to authenticated users or public access without migrating cards.
- Ordinary card collections are hard-scoped to one pool. An `all pools` option is reserved for explicit staff management tools and must not become a normal workspace.
- Hero is excluded by default in each workspace. Boon and Event are not globally excluded.
- Cross-pool links do not automatically change the active workspace. A linked Player Hero opened from a Game Master card is visibly labeled Player, while Back/return navigation preserves the Game Master workspace.
- Player deck building and Playtester remain Player-only unless a later feature explicitly defines Game Master equivalents.

## Authoritative success condition

The step succeeds when every normal card-derived collection request carries one explicit pool, the sidenav and route state agree on the active workspace, unauthorized users cannot enter or retain the Game Master workspace, and backend tests/checks confirm that direct URLs and assets remain protected.

Local preference persistence is convenience only. The session capability and current route are authoritative for whether Game Master context may be used.

## Workspace state design

Add code-owned frontend pool types and labels under `frontend/src/domain/cards`. Own reusable pool query behavior with the card domain; keep shell placement and global route orchestration under `frontend/src/app`.

The workspace state contains:

- active pool: `player` or `game_master`;
- whether the current session may access Game Master cards;
- the last permitted pool preference.

Persist the preference with the existing VueUse/local-storage conventions. On initialization:

1. Read the session capability.
2. Read a valid route pool when the route supports pool context.
3. Otherwise use the last permitted preference.
4. Fall back to Player.

When authentication or capability changes remove Game Master access, synchronously switch to Player, replace any Game Master route/query state, clear disallowed cached collection data, and only then issue new requests. Logging out from Game Master context must never leave a flash of protected data.

Use the existing route filter/query infrastructure. `card_pool` remains shareable in card-gallery URLs; direct card detail routes derive the card's actual pool after loading and preserve the caller's explicit return location.

## Sidenav and navigation

Update `frontend/src/app/components/AppShellNav.vue` with a prominent two-option control near the application identity and before primary navigation.

- All users see Player as the active context.
- Only users with Game Master capability see the Game Master option.
- Collapsed desktop navigation uses an accessible compact control or menu with an unambiguous tooltip/label.
- Mobile navigation exposes the same state and behavior.
- Switching workspaces closes the mobile drawer and navigates to the target workspace's safe landing route.

Player workspace navigation initially contains:

- Gallery
- Decks
- Playtester
- My Decks when authenticated
- Build a deck when authenticated
- Notifications and Settings under their existing access rules

Game Master workspace navigation initially contains:

- Gallery
- Notifications and Settings under their existing access rules
- future Game Master-specific entries only when implemented

Staff operational navigation such as Imports, Operations, Review Queue, and Admin stays separated below the existing divider and remains accessible from either workspace. Imports should prefill their pool from the active workspace, while still displaying and requiring the pool field specified in Step 2.

## Collection and route scoping

Apply the active pool explicitly to every relevant frontend request:

- gallery and grouped gallery;
- card search/select controls;
- card group views and embedded previews;
- catalog linked-card previews;
- exports initiated from a card collection;
- deck-builder hero and card galleries;
- Playtester deck/card preview surfaces;
- any app-wide card counts or suggestions.

Player deck, deck-builder, and Playtester requests always send `card_pool=player`, even if a staff user has Game Master as the shell workspace. If those routes are not offered in Game Master navigation but are reached directly, keep their Player classification explicit and show the Player workspace or route back to a safe Game Master page according to the route guard.

On a workspace switch, discard the outgoing collection result before fetching the incoming pool. Do not show stale Player cards under a Game Master heading or vice versa.

Gallery defaults in each pool:

- active cards;
- current workspace pool;
- Hero excluded;
- other role filters empty.

Switching pool resets transient gallery filters to these defaults for the target pool in the first implementation. Preserve pagination, selection, and export state only when it is valid for the target pool; otherwise clear it explicitly.

## Backend capability and authorization audit

Step 1 introduces the central capability and baseline protection. This step must perform a complete audit rather than assuming the navigation is sufficient.

Verify the central function (for example `can_access_game_master_cards`) is used by:

- card list/grouped list queries;
- card detail, version, generation, and image endpoints;
- immutable image asset resolution;
- groups and embedded card payloads;
- catalog counts/previews;
- exports and TTS surfaces;
- deck validation and public deck serialization;
- notifications or activity payloads that embed card details;
- developer-data download/import policy where Game Master cards are included.

Expose a named session capability such as `can_access_game_master_cards`. The frontend consumes that capability and does not infer it from `is_staff`, even though staff is the initial policy.

If the future policy changes, the intended edit points are the backend capability policy, session payload, and access-control documentation—not card rows, pool values, or gallery logic.

## Cross-pool relationships

Do not add a generic same-pool restriction. Game Master Boons/Events may intentionally link to Player Heroes.

For any existing or future relationship serializer:

- authorize the target card independently;
- include the target's `card_pool` and `card_roles`;
- display a pool badge when the target differs from the active workspace;
- preserve the originating return route/workspace;
- never expose an unauthorized Game Master target through a Player/public relationship payload.

This step does not create a new link model. It establishes behavior for relationships that already exist or are added later.

## Frontend ownership

- Card pool contracts, request parameters, labels, and reusable preference helpers belong in `frontend/src/domain/cards`.
- Sidenav rendering, global route synchronization, auth-transition handling, and workspace-aware nav composition belong in `frontend/src/app`.
- Gallery filter state continues to use the existing card filter utilities.
- Import prefill remains in `frontend/src/features/import-jobs` and consumes the domain/app workspace contract without importing another feature.
- Do not create feature-to-feature imports or a second pool state owned by Imports, Gallery, or Decks.

All visible changes must use semantic theme primitives and be verified in light and dark modes.

## Implementation sequence

1. Confirm Step 1 capability enforcement and Step 2 explicit import pool are complete.
2. Add the frontend card-pool workspace/preference contract and tests.
3. Expose and consume the named session capability.
4. Add desktop, collapsed, and mobile sidenav controls.
5. Make nav item composition workspace-aware.
6. Synchronize workspace, route query, auth changes, and safe landing routes.
7. Scope gallery and all reusable card collection clients.
8. Lock deck building and Playtester to Player explicitly.
9. Prefill, but do not hide, the import pool from the active workspace.
10. Audit all backend card-derived payloads and assets for capability enforcement.
11. Update current-state card, import, access, deck, and Playtester documentation.
12. Run all permitted validation and manually verify both themes and responsive nav modes.

## Required tests

Add or update tests covering:

- Player default with no stored preference;
- permitted Game Master preference restoration;
- invalid/disallowed stored values falling back to Player;
- logout, staff removal, or session refresh while Game Master is active;
- desktop, collapsed, and mobile toggle behavior;
- workspace-specific nav item composition;
- safe landing routes and route-query synchronization;
- clearing stale collections during a switch;
- gallery Hero-excluded defaults in both pools;
- every collection request carrying an explicit pool;
- deck builder and Playtester remaining Player-scoped;
- import pool prefill without removing explicit confirmation;
- direct cross-pool links preserving the originating workspace;
- unauthorized Game Master list requests returning `403`;
- unauthorized Game Master object/image access returning `404`;
- staff access to all corresponding surfaces.

Do not run prohibited service/integration suites. Run affected permitted frontend tests, lint and typecheck for touched packages, Django checks, and manual browser verification at `http://localhost:8888` when the local app is available.

## Acceptance criteria

- Player/Game Master is the primary sidenav context on desktop and mobile.
- The Game Master option is visible only through the named capability.
- Player is the safe default and automatic fallback after access loss.
- Normal galleries never mix pools.
- Hero is excluded by default in both workspaces.
- Player deck building and Playtester never admit Game Master cards.
- Imports visibly prefill the current workspace while retaining explicit pool confirmation.
- Staff tools remain reachable from either workspace.
- Direct cross-pool relationships render with pool context and no unauthorized data leak.
- Changing the future Game Master access audience requires a centralized policy change, not data migration.
- Light/dark, expanded/collapsed desktop, and mobile navigation are verified.
- Lint, typecheck, Django checks, affected permitted tests, and documentation validation pass.

## Explicit non-goals

- Game Master deck building or Playtester behavior.
- New Game Master-specific tools beyond the scoped Gallery.
- A new card-to-card relationship model.
- Public or ordinary authenticated Game Master access in the initial release.
- An ordinary mixed-pool gallery.
- Automatic workspace changes when following cross-pool links.
