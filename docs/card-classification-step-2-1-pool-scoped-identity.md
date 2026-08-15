# Card Classification Step 2.1: Pool-Scoped Card Identity

Post-feature TTS amendment: pool-scoped identity is now also carried by persistent TTS sheets and slots. Player, Evil, and Neutral each allocate into separate sheet buckets, while every pool uses the same stable public sheet URL so existing TTS objects see later rerenders. Gallery and content-version export creation can use authorized restricted pools, while developer-data and decks retain their explicit Player-only product scope. References below to all public artifacts remaining Player-only describe this checkpoint's initial boundary.

Status: implemented, validated, and merged into the classification umbrella branch. All dependent classification checkpoints through Step 3.2 are also implemented and merged.

Target amendment: this document records the implemented pool-scoped identity seam. [Step 2.3](card-classification-step-2-3-faction-classification.md) extends that seam so normalized names, aliases, and untargeted image matching are scoped by pool plus the exact canonical faction set, allowing same-name cards in different factions within one pool.

This checkpoint sits between import inference and import workflow consolidation:

1. [Card classification foundation](card-classification-step-1-foundation.md)
2. [Authorization seam consolidation](card-classification-step-1-1-authorization-seam.md)
3. [Import inference](card-classification-step-2-import-inference.md)
4. Pool-scoped card identity (this document)
5. [Import workflow seam consolidation](card-classification-step-2-2-import-workflow-seam.md)
6. [Faction classification](card-classification-step-2-3-faction-classification.md)
7. [Card-pool workspaces](card-classification-step-3-card-pool-workspaces.md)
8. [Context-preserving workspace switching](card-classification-step-3-1-context-preserving-workspace-switching.md)

Do not begin Step 2.2 until this checkpoint is merged into the classification umbrella branch. This step changes stable identity and every path that resolves it; Step 2.2 can then consolidate import lifecycles without preserving a globally scoped lookup.

## Outcome

Replace the temporary Player/Game Master pool model with the final three pools—Player, Evil, and Neutral—and allow the same normalized card name to exist independently in each pool.

After this step:

- stable name identity is the pair `(card_pool, normalized_key)`;
- every card belongs to exactly one of `player`, `evil`, or `neutral`;
- the same name or alias may exist once in each of the three pools;
- same-pool imports continue to resolve the existing stable card;
- cross-pool imports create and maintain independent cards, even when their image bytes are identical;
- Evil and Neutral share one centralized restricted-pool access policy whose initial audience is staff;
- roles remain classification on an identity and never participate in identity matching;
- renames, aliases, pool moves, merges, and developer-data use the same pool-scoped rules as imports;
- card ids remain the canonical identifier for URLs, relationships, and mutations.

## Why this checkpoint exists

Step 2 correctly snapshots one explicit pool for each import batch, but it currently exposes the temporary values `player` and `game_master` and its persistence lookup is still global:

- `Card.key` is globally unique;
- `CardAlias.key` is globally unique;
- untargeted imports search latest `CardVersion.image_hash` without a pool;
- name and alias resolution does not accept a pool;
- rename conflict checks do not accept a pool;
- developer-data selection uses card keys in queries that can see every pool.

The product model now requires Player, Evil, and Neutral as independent pools. There are no existing Game Master cards that require semantic migration. Fixing only the choice list or name query would still leave checksum, alias, rename, authorization, and developer-data paths with the old two-pool assumptions.

## Locked decisions

- The only supported persisted pool values after this checkpoint are `player`, `evil`, and `neutral`. Remove `game_master` from new model, API, import, and frontend contracts.
- No Game Master card data is migrated because none exists. The migration must preflight persisted pool-bearing rows and fail clearly if an unexpected `game_master` value exists instead of guessing whether it means Evil or Neutral.
- A stable card's human-readable import identity is `(card_pool, normalized name or alias)`.
- `Card.id` remains globally unique and authoritative. Pool-scoped keys are natural lookup keys, not replacements for ids in URLs or relationships.
- Card roles do not participate in identity. A role difference within one pool remains a classification mismatch on the same card; it must not create another card.
- Untargeted image-hash matching is scoped to the import job's selected pool.
- Identical artwork in different pools may share hash-addressed stored bytes, but it produces separate `Card` and `CardVersion` rows. Storage deduplication must not imply domain identity.
- Targeted reparses remain id-driven. Their target card/version snapshot is authoritative and they do not switch identities through a name or checksum lookup.
- Primary keys and aliases are unique within a pool, not globally.
- A primary key may not collide with another card's alias in the same pool. The same normalized value in the other pool is allowed.
- Moving a card to another pool is an explicit identity move. The card and all of its aliases move atomically or nothing moves.
- A destination-pool collision blocks a pool move with a clear validation error. Do not silently merge, rename, drop aliases, or create a suffix.
- Card merges remain same-pool only. Moving a card explicitly is required before a merge can collapse the identities.
- Existing-card classification remains authoritative only after a match inside the requested pool. A same-name card in the other pool is not a classification mismatch.
- Evil and Neutral use the same centralized restricted-pool authorization policy, initially staff-only. Authorization code reasons about allowed pool scopes rather than special-casing either pool.
- Neutral remains a separate stable pool. Player and Evil views do not include Neutral implicitly in this checkpoint.
- A future view may explicitly compose Neutral with Player or Evil results. That must be an authorized multi-pool query/view preference, not multiple pool ownership, silent backend expansion, or duplicated card rows.
- The current developer-data format remains Player-only and does not need a format bump. Its natural keys are unambiguous inside that fixed pool scope.
- Do not encode the pool into `Card.key`, add visible key prefixes, or rely on frontend filtering to make globally unique persistence appear pool-scoped.

## Authoritative success condition

The step succeeds when `game_master` is absent from current pool contracts, every untargeted import identity lookup requires one explicit Player/Evil/Neutral pool, the database permits one normalized primary or alias key per pool, and all identity mutations enforce that invariant atomically.

A successful parser item is authoritative only when its resulting `Card.card_pool` equals the import job's selected pool for untargeted work. A warning or frontend badge is not a substitute for persisting the correct identity.

## Data model and migration

Implement the schema in `services/core/src/card_reader_core/models` and a new core migration after the Step 2 migrations.

### Pool values

- Keep `player` as the default.
- Replace `game_master` with `evil` and add `neutral` in the code-owned pool registry.
- Derive model choices, validation, API filter metadata, import validation, and frontend pool metadata from the appropriate centralized registry in each runtime.
- Do not retain `game_master` as an accepted API alias or silently map it to Evil.

Before altering contracts, assert that no `Card`, `ImportJob`, import-item target snapshot, or other persisted pool-bearing row contains `game_master`. Because this feature is not deployed and no Game Master card data exists, do not define a value mapping to Evil or Neutral. An unexpected leftover value should produce an actionable migration/preflight failure so local development data can be reset or corrected deliberately.

### Card primary key

- Remove global uniqueness from `Card.key` while retaining an index suitable for normalized-key lookups.
- Add a database uniqueness constraint on `(card_pool, key)`.
- Keep `Card.id` unchanged as the primary key.

### Pool-scoped aliases

Add a required `CardAlias.card_pool` field using the same code-owned pool choices as `Card.card_pool`.

The migration must:

1. Create and seed one `CardIdentityPoolLock` row for each final pool.
2. Add the alias pool as nullable.
3. Backfill it from each alias's owning card.
4. Reject pre-existing same-pool primary/alias collisions.
5. Make the alias pool required and indexed.
6. Remove global uniqueness from `CardAlias.key`.
7. Add a uniqueness constraint on `(card_pool, key)`.
8. Replace `Card.key` global uniqueness with `(card_pool, key)` uniqueness.
9. Apply the final Player/Evil/Neutral choices to every persisted pool field.

The model cannot express `CardAlias.card_pool == CardAlias.card.card_pool` as a portable cross-table check constraint. Enforce that invariant through the one core identity mutation seam and cover direct repository writes with tests. Do not scatter alias creation or pool updates through callers.

Migration reversal may restore global uniqueness only when no key is duplicated across pools. Add a preflight data check that fails with a clear message rather than partially reversing or choosing one card. No production compatibility rewrite is required before deployment, but the migration must preserve all current rows in the forward direction.

Update `services/core/src/card_reader_core/db/schema_check.py` if its required-column checks are affected, and update `docs/card-database-diagram.svg` in the implementation.

## Pool registry and restricted access

Make the core pool registry the backend source of truth for keys, labels, ordering, choices, and filter metadata:

1. Player (`player`)
2. Evil (`evil`)
3. Neutral (`neutral`)

Remove `GAME_MASTER_CARD_POOL`, Game-Master-specific validation branches, and string comparisons after all callers use the final registry. Keep `PLAYER_CARD_POOL_SCOPE` as the fixed public-artifact scope and evolve `ALL_CARD_POOLS_SCOPE` to contain all three values.

The API auth boundary continues mapping a user to `CardPoolScope`:

- anonymous and ordinary authenticated users receive Player only;
- staff receive Player, Evil, and Neutral;
- Evil and Neutral collections explicitly requested without access return `403`;
- direct Evil or Neutral cards, versions, images, and assets return `404` to unauthorized callers.

Rename any public `can_access_game_master_cards` session field and internal `allow_game_master_cards` vocabulary rather than cloning it for each restricted pool. Expose `accessible_card_pools` in canonical order and let frontend pool controls derive their permitted options from that list. The centralized policy remains the only place where staff maps to the restricted pools.

Audit derived behavior through the scope rather than adding Evil/Neutral branches: embedded payloads, groups, catalog previews/counts, exports, TTS allocation and rendering, notifications, deck validation/placeholders, parse flags, and developer-data. Developer-data remains Player-only; TTS allocation and rendering use explicit pool buckets with stable public sheet URLs.

## Core identity seam

Give card identity one core-owned API, either by evolving the current card-merge alias helpers or moving the shared behavior to an owned cards identity module. Import repositories, manual edits, version promotion, merges, and developer-data must consume it instead of rebuilding filters.

The seam owns:

- resolving a normalized primary key or alias inside one required pool;
- validating primary-key and alias conflicts inside one required pool;
- creating an alias with the owning card's pool;
- renaming a card while preserving its prior same-pool alias;
- moving a card and all aliases to a destination pool atomically;
- returning typed conflict information that API serializers can present without parsing database errors.

Require `card_pool` at call sites that resolve an identity. Do not keep a defaulted global resolver for convenience. Helpers operating on a loaded card may derive the pool from that card.

Use database constraints as the final race-safe boundary for same-table collisions and one durable lock row per pool to serialize primary and alias writes across their two tables. Every identity mutation acquires the appropriate pool lock through the cards identity seam before checking or writing the namespace. Convert uniqueness or lock-contention errors raised by concurrent creates or moves into the same domain conflict used by preflight checks. A larger per-name registry table remains outside this checkpoint.

## Import persistence behavior

Update the untargeted parser persistence path in `services/core/src/card_reader_core/repositories/cards`.

Resolve in this order, always inside the import job's selected `card_pool`:

1. If `reparse_existing` is enabled, find a latest version with the same image hash whose card is in the selected pool.
2. Otherwise resolve the parsed normalized name against primary keys and aliases in the selected pool.
3. If neither lookup matches, create a new card in the selected pool and apply the resolved role set.
4. Create or update the version using the existing content-version and snapshot rules.
5. Finalize evidence and warnings against the card that was resolved inside that pool.

The lookup must produce these outcomes:

| Existing state | Import request | Result |
| --- | --- | --- |
| Player `Fireball` | Player `Fireball` | Existing Player card |
| Player `Fireball` | Evil `Fireball` | New Evil card |
| Player `Fireball` | Neutral `Fireball` | New Neutral card |
| Evil `Fireball` | Neutral `Fireball` | New Neutral card |
| Player alias `Old Fireball` | Player `Old Fireball` | Existing Player card |
| Player alias `Old Fireball` | Evil `Old Fireball` | New Evil card |
| Same image hash in Evil | Neutral import | Independent Neutral card/version |
| Same name and pool, different inferred roles | Same-pool import | Existing card plus classification mismatch warning |

Do not use the role set to select between same-name cards. The database invariant guarantees at most one name/alias match inside a pool.

Targeted reparses continue to load `target_card_id` and `target_card_version_id`, verify ownership, and preserve live classification. Their queued-classification-change warning remains separate from untargeted identity resolution.

## Rename, pool move, and merge behavior

### Rename and version promotion

Both manual name edits and latest-version promotion must validate the new normalized key only inside the card's current pool. On success, preserve the previous key as an alias in that pool. A key used only in the other pool does not block the rename.

### Pool move

Before changing `Card.card_pool`:

1. Lock the card and its alias rows inside one transaction.
2. Check the card's primary key against destination-pool cards and aliases.
3. Check every alias against destination-pool cards and aliases.
4. Update the card pool and every alias pool together.
5. Preserve roles, versions, relationships, deck references, and stable id.

If any conflict exists, reject the edit and leave the card and aliases in the original pool. Keep existing warnings or invalid-state behavior for deck references; this step does not delete or rewrite decks.

### Merge

Keep the existing different-pool merge rejection. Same-pool merge previews, alias transfer, and conflict detection must use the shared pool-scoped identity seam. Transferred aliases retain the target pool. Merge redirects remain id-based and globally unambiguous.

## Developer-data and other natural-key consumers

Developer-data bundles remain constrained to the fixed Player artifact scope. Update selection and validation so:

- `selection.json` card keys resolve only against Player cards;
- same-key Evil and Neutral cards are ignored rather than reported as restricted selected cards;
- a selected key is missing only when no Player card has that key;
- exported card and group references remain unique within the Player payload;
- importing a Player bundle may coexist with same-key Evil and Neutral cards in the destination database.

Do not bump the bundle format solely for this change. If a future format includes more than one card pool, it must make natural references pool-qualified or id-based and receive a deliberate format version bump.

Audit every remaining `Card.key`, `CardAlias.key`, and `image_hash` lookup. Classify each use as:

- id-driven and unaffected;
- operating on an already pool-scoped queryset;
- requiring an explicit pool parameter;
- intentionally limited to the Player developer-data scope.

CSV fields and display payloads may continue exposing `card_key`, but clients must not treat it as globally unique. Mixed-pool management surfaces must include the existing pool classification beside duplicate labels. URLs, relations, updates, groups, decks, notifications, and merge redirects continue using card ids.

## API and frontend impact

No new public request field is required: Step 2 already makes import `card_pool` explicit and card records already expose pool and id. Change the accepted values to `player|evil|neutral` and reject `game_master`.

Rename Game-Master-specific entitlement booleans to pool-oriented scope contracts. The backend authorization boundary should expose the allowed `CardPoolScope`; the session payload should expose an ordered `accessible_card_pools` list for frontend feature detection instead of adding separate `can_access_evil_cards` and `can_access_neutral_cards` flags. Staff initially receive all three pools and everyone else receives Player only.

Update API error handling so a rename or pool-move collision returns a stable validation response rather than an unhandled database error. Preserve the existing Card-tab editing contract.

Audit selectors that can show multiple pools, especially Admin Catalog and merge/search tooling. Duplicate names must remain distinguishable through an always-visible Player, Evil, or Neutral badge. Ordinary gallery requests remain single-pool; the global workspace remains Step 3.

## Implementation sequence

1. Capture current name, alias, checksum, rename, pool-move, merge, and developer-data behavior in focused regression tests.
2. Replace the temporary Game Master pool contract with Evil and Neutral across core, API, import snapshots, filter metadata, and frontend registries; add the no-existing-value migration preflight.
3. Rename the centralized entitlement/session contract to pool-scope terminology and grant staff all three pools.
4. Add `CardAlias.card_pool` and the pool-scoped database constraints through the new migration.
5. Introduce the central pool-scoped card identity resolver and mutation helpers.
6. Migrate alias creation, rename, latest-version promotion, pool editing, and merge preview/execution to the seam.
7. Scope untargeted checksum and name/alias import matching to the selected import pool.
8. Adjust classification evidence so cross-pool names create independent cards while same-pool role differences still warn.
9. Scope developer-data key selection and adoption to Player cards.
10. Audit remaining natural-key and image-hash consumers and make their pool assumptions explicit.
11. Update management UI disambiguation where a mixed-pool selector can display all three pools.
12. Update the database diagram and current-state card/import/access/developer-data documentation.
13. Run all permitted validation and resolve failures before beginning Step 2.2.

## Required tests

### Schema and identity

- only `player`, `evil`, and `neutral` are accepted after migration, and unexpected persisted `game_master` values fail preflight clearly;
- the canonical backend and frontend pool metadata order is Player, Evil, Neutral;
- the same normalized `Card.key` is allowed in different pools and rejected within one pool;
- the same normalized alias key is allowed in different pools and rejected within one pool;
- alias pool is backfilled from its card and remains synchronized after mutations;
- primary-key/alias collisions are rejected within one pool and allowed across pools;
- concurrent same-pool creates resolve to one identity or a typed conflict rather than duplicate rows;
- reverse migration reports cross-pool duplicates clearly before attempting global uniqueness.

### Import persistence

- same name, different artwork, different pool creates two cards;
- same name and same artwork hash, different pool creates two cards and versions;
- same primary name in the same pool resolves the existing card;
- same alias in the same pool resolves the existing card;
- an alias that exists only in the other pool does not match;
- same-pool role disagreement preserves the existing roles and emits the mismatch warning;
- cross-pool same-name import does not emit a classification mismatch warning;
- exact role overrides and automatic inference behave identically with respect to identity;
- targeted reparses remain bound to their target ids and preserve queued/live classification warnings.

### Mutations and merges

- rename is blocked by a primary or alias collision in the same pool and allowed when the collision exists only in the other pool;
- a successful rename creates a same-pool alias for the old key;
- a pool move updates the card and every alias atomically;
- any destination collision rolls back the entire pool move;
- roles, versions, groups, and deck references survive a successful pool move;
- same-pool merges retain aliases and redirects;
- cross-pool merge preview and execution remain blocked.

### Developer-data and clients

- Player selection resolves the Player card when same-key Evil and Neutral cards exist;
- a same-key Evil or Neutral card alone does not satisfy a Player selection;
- Evil and Neutral twins are not falsely reported as explicitly selected restricted cards;
- Player bundle export/import round-trips while same-key Evil and Neutral cards coexist;
- mixed-pool Admin Catalog/search results visibly disambiguate duplicate names;
- APIs and routes continue addressing each duplicate-name card independently by id.
- session pool metadata returns Player only for ordinary users and Player/Evil/Neutral for staff without separate per-pool booleans;
- unauthorized Evil/Neutral collection requests return `403`, while their direct objects and assets return `404`;
- developer-data, deck, and embedded-payload behavior excludes both restricted pools through the shared scope; TTS sheets are pool-partitioned public artifacts, notification inboxes use each recipient's scope, and deck-version delivery remains Player-only;

## Validation

Do not run prohibited service/integration suites locally. Run:

```text
pnpm --filter @card-reader/core lint
pnpm --filter @card-reader/core typecheck
pnpm --filter @card-reader/api lint
pnpm --filter @card-reader/api typecheck
pnpm --filter @card-reader/web lint
pnpm --filter @card-reader/web typecheck
pnpm --filter @card-reader/web test -- <affected card editor/catalog specs>
uv run --project ../.. --package card-reader-api python manage.py check
```

Add focused core/API tests for the matrix above, validate migration forward behavior and guarded reversal, validate the SVG XML, and manually verify any changed mixed-pool management UI in light and dark themes.

## Acceptance criteria

- Player, Evil, and Neutral are the only supported pools; `game_master` is absent from current contracts.
- Player, Evil, and Neutral cards may share a normalized primary name without sharing a stable card identity.
- Untargeted imports never match a card or latest image hash outside the selected pool.
- Same-pool name and alias imports preserve existing-card behavior.
- Roles remain independent, multi-valued classification and never fork identity.
- Primary and alias uniqueness is enforced per pool with centralized conflict handling.
- Rename, version promotion, pool move, and merge behavior uses the same identity rules as import.
- Pool moves are atomic and cannot strand aliases in the old pool.
- Cross-pool merges remain rejected.
- Evil and Neutral share the centralized restricted-pool policy and remain staff-only initially.
- Neutral is not mixed into Player or Evil queries implicitly.
- Developer-data remains Player-scoped and works when same-key Evil and Neutral cards exist.
- Mixed-pool management surfaces distinguish duplicate names, while id-based routes and relationships remain unambiguous.
- Database diagram and current-state documentation match the implemented schema.
- Lint, typecheck, Django checks, affected permitted tests, migration checks, diagram validation, and documentation validation pass.

## Explicit non-goals

- Using roles as identity or restricting which roles may exist in a pool.
- Automatically merging existing cross-pool cards.
- Adding visible pool prefixes or generated suffixes to card names or keys.
- Changing import inference policy, templates, tags, or override semantics.
- Refactoring upload lifecycle, cleanup, grouped reparses, or frontend activity state; those belong to Step 2.2.
- Adding the Player/Evil/Neutral sidenav workspace or Neutral overlays; those belong to Step 3 or a later filter pass.
- Changing the initial staff-only restricted-pool authorization audience.
- Designing Evil/Neutral decks, scenarios, or Playtester behavior.
- Expanding developer-data bundles to multiple pools.
