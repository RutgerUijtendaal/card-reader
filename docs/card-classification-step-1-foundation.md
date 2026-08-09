# Card Classification Step 1: Foundation

Status: implemented and validated.

This is the first of three ordered plans:

1. Card classification foundation (this document)
2. [Import inference](card-classification-step-2-import-inference.md)
3. [Player and Game Master workspaces](card-classification-step-3-player-gm-workspaces.md)

Do not begin Step 2 or Step 3 until this step's acceptance criteria are satisfied. Later steps may be implemented in the same branch only when each step remains independently reviewable and verified.

## Outcome

Replace the single `Card.is_hero` flag with two card-level classification dimensions:

- Every card belongs to exactly one pool: `player` or `game_master`.
- Every card has zero or more roles: initially `hero`, `boon`, and `event`.
- A card with no roles is displayed and filtered as **Standard**. `standard` is not persisted as a role.

The existing Player experience must continue to work, Hero behavior must use the new role system, Game Master cards must be protected by a central staff-only capability, and staff must be able to edit and query both dimensions. Import inference and the global workspace toggle are deliberately deferred.

## Locked decisions

- Pool and roles belong to the stable `Card` identity, not `CardVersion` or `Template`.
- Template selection remains version-level parsing configuration.
- Roles are additive and may coexist. Do not encode them as mutually exclusive choices or separate booleans.
- `standard` means the absence of special roles. Never persist `standard` beside `hero`, `boon`, or `event`.
- Typical pool/role combinations such as Player Hero and Game Master Boon/Event are conventions, not database constraints. Any restrictions or warnings belong in core code.
- Cross-pool relationships are allowed. Do not add same-pool database constraints to groups, future card links, or other card relationships.
- Game Master access is controlled through a named backend capability whose initial policy is `is_staff`. Do not scatter direct `is_staff` checks through card queries and views.
- Public derived artifacts such as developer-data bundles and unauthenticated TTS card sheets are Player-pool scoped. They must not encode the current staff policy; changing who receives the Game Master capability must remain independent from deciding which artifacts are public.
- Unauthorized list/filter requests that explicitly request the Game Master pool return `403`. Unauthorized direct access to a Game Master card, version, or image returns `404` to avoid disclosing the object.
- The ordinary gallery defaults to Player cards with Hero excluded. This is a frontend default, not a hidden backend default for every card query.

## Authoritative success condition

The step succeeds when `Card.is_hero` is no longer a persisted or writable source of truth; all existing Hero-dependent behavior reads the `hero` role; every existing card has the Player pool; Game Master cards cannot leak through public APIs or assets; and pool/roles can be edited and filtered by staff.

Migration completion is authoritative for schema/data conversion. Frontend state or cached responses must not be treated as evidence that the migration succeeded.

## Data model

Implement the schema in `services/core/src/card_reader_core/models` and a new core migration.

### Card pool

Add a required, indexed `Card.card_pool` character field with code-owned values:

- `player`
- `game_master`

The database default and migration backfill are `player`. Expose normalization and validation helpers from the card model/service owner instead of duplicating allowed values in serializers and clients.

### Card roles

Add a `CardRoleAssignment` model with:

- its normal timestamp/id fields following repository conventions;
- a `card` foreign key with cascade deletion and a clear reverse name such as `role_assignments`;
- a `role` field using the code-owned values `hero`, `boon`, and `event`;
- an indexed uniqueness constraint on `(card, role)`.

Use assignment rows rather than a JSON array on `Card` so gallery filters remain portable and queryable on SQLite. Do not create a mutable role catalog table: supported top-level roles are application behavior and are released with code.

Add core helpers for:

- normalizing and validating role keys;
- obtaining the normalized role set for a card;
- testing whether a card has a role, especially `card_has_role(card, "hero")`;
- transactionally replacing a card's role set;
- expressing role filters, including the derived Standard state.

Callers should use the public card service/repository APIs rather than manually writing assignment rows.

### Migration

The migration must:

1. Add `Card.card_pool` with `player` as the default.
2. Create the role-assignment table and uniqueness constraint.
3. Create a `hero` assignment for every card whose existing `is_hero` is true.
4. Leave non-Hero cards with no role assignments, making them Standard.
5. Remove `Card.is_hero` only after the data migration is defined.
6. Provide a meaningful reverse migration that restores `is_hero` from the Hero assignments before removing the new structures.

Update `services/core/src/card_reader_core/db/schema_check.py` if it enumerates required schema columns, and update `docs/card-database-diagram.svg` in the same implementation.

## Core and repository changes

Update card query row types and repository functions under `services/core/src/card_reader_core/repositories/cards` to prefetch or annotate roles without N+1 queries.

Support these normalized filter concepts:

- one `card_pool` value;
- included role values;
- excluded role values;
- `any` or `all` inclusion matching;
- the synthetic filter value `standard`, which matches cards with no role assignments.

If `standard` is combined with other included roles, `any` may match either Standard or one of those roles. Reject `all` when `standard` is combined with a persisted role because no card can satisfy both states. Exclusions take precedence.

Replace every domain use of `is_hero`, including:

- deck creation, normalization, validation, and hero selection;
- deck exports and hero summaries;
- Playtester hero-zone initialization contracts;
- developer-data validation, import, export, and coverage checks;
- notification example seeds;
- card merge/edit behavior;
- management checks and any other repository query.

Deck rules remain unchanged: a deck hero must be a Player card with the Hero role, Hero cards cannot become normal mainboard entries where the current rules prohibit that, and existing deck references are not deleted during classification edits. Manual Card-tab classification edits are authoritative and must remain possible. When staff remove Hero or move a referenced card to the Game Master pool, preserve every deck reference and surface the resulting warning or invalid state so owners can resolve it deliberately.

### Developer-data contract

Treat card classification as a developer-data format change, not an incidental exporter edit.

- Bump `DEVELOPER_DATA_FORMAT_VERSION` from 1 to 2 for newly generated bundles.
- Version 2 `CardRecord` replaces `is_hero` with required `card_pool` and canonical `card_roles` fields.
- Keep a version-aware Version 1 import adapter that maps every card to Player and maps `is_hero=true` to the Hero role. Do not weaken the strict Version 2 schema with permanently optional classification fields.
- New Version 2 bundles must not emit `is_hero`.
- Update exporter, importer, archive validation, isolated publication validation, counts/doctor checks, and any schema fixtures together.
- Replace Hero-boolean coverage evaluation with role-aware coverage and add pool-aware coverage. Preserve the current effective Hero minimum under the Hero role; Game Master/Boon/Event minimums may remain zero until reviewed data exists.
- Update `dev-data/selection.json` to the new coverage shape when the implementation lands.
- Do not hand-edit `dev-data.lock.json`. Publish and validate a compatible immutable bundle, then commit the generated lock with its new bundle version, format version, and checksum. Until that bundle exists, the application must remain able to consume the pinned Version 1 bundle through the adapter.
- Update `docs/developer-data.md` with the supported-format and adoption behavior.

## API contract

Update `services/api/src/card_reader_api/cards` and every embedded card serializer.

Card payloads expose:

```json
{
  "card_pool": "player",
  "card_roles": ["hero"]
}
```

Role arrays are stable, deduplicated, and sorted in the code-owned display order. Remove writable `is_hero` handling and migrate all first-party clients in the same step so there is one source of truth.

Card editing accepts `card_pool` and a complete replacement `card_roles` array on the Card-level update contract. Validate values before calling the core service. Version-level update and reparse contracts must not own these fields.

Card list/filter contracts accept:

- `card_pool=player|game_master`;
- repeated `card_roles=standard|hero|boon|event`;
- repeated `card_role_exclude=standard|hero|boon|event`;
- `card_role_match=any|all`.

When `card_pool` is omitted from an ordinary public card collection, use `player`. Staff management callers may explicitly choose either pool. Add the role/pool display options needed by clients to `GET /cards/filters` rather than duplicating labels and ordering in feature code.

Apply the classification and access policy consistently to:

- paginated and grouped gallery queries;
- card detail and generation endpoints;
- current and historical card images, including immutable asset paths;
- card groups and embedded group members;
- catalog linked-card counts/previews;
- Admin Catalog linked-card and suggestion-occurrence payloads, including `card_pool` and `card_roles` on every card preview;
- search selectors;
- CSV and TTS exports;
- deck-building card selection and any card-derived public count.

Centralize authorization through a capability such as `can_access_game_master_cards(user)`. Add the corresponding session capability for frontend feature detection. The server remains authoritative.

## Frontend changes

Update card contracts under `frontend/src/domain/cards` and remove `is_hero` from first-party TypeScript models.

In the Card tab of the staff editor:

- replace the Hero checkbox with a required Player/Game Master pool control;
- add multi-select role controls for Hero, Boon, and Event;
- show Standard when no roles are selected;
- keep lifecycle and deck-building configuration in the same Card tab;
- surface backend validation when changing a referenced Hero or pool.

Extend the existing card filter architecture rather than adding page-local parsing:

- normalization in `cardFilterState.ts`;
- route serialization in `cardFilterRouteState.ts`;
- catalog/id translation in `cardFilterSelection.ts` where applicable;
- API payload construction in `cardFilterRequest.ts`;
- visible controls in the shared card filter components.

The gallery initializes with `card_pool=player` and Hero excluded. Staff receive a pool filter so Game Master cards remain manageable before Step 3 adds the global workspace toggle. Non-staff never receive a Game Master option from capabilities and cannot bypass the server by editing the URL.

Update deck-builder queries from `is_hero=true|false` to role filters. Player deck and Playtester surfaces must always request the Player pool explicitly.

Update the Admin Catalog's existing `CatalogLinkedCardsGrid` and its suggestion-occurrence use:

- extend `LinkedCardPreview` and `SuggestionOccurrencePreview` through the core service, API serializer, and frontend types with `card_pool` and `card_roles`;
- show a compact Player/Game Master pool badge on every linked-card tile;
- show canonical Hero, Boon, and Event role badges, or a Standard badge when the role array is empty;
- keep the classification visible without requiring hover or opening the card detail;
- reuse the code-owned labels/order from the card domain instead of defining Admin-only role names;
- preserve the existing image preview, hover behavior, and link back to the selected catalog entry.

Verify all new controls in light and dark themes.

## Implementation sequence

1. Add core pool/role constants, models, helpers, and the reversible migration.
2. Update card repositories, services, and Hero-dependent core behavior.
3. Add the central Game Master capability and enforce it across card-derived API surfaces.
4. Update API payloads, edit validation, filter metadata, query parameters, and embedded serializers.
5. Update developer-data contracts and management checks.
6. Update frontend card models, editor controls, filters, and Hero-dependent consumers.
7. Update the schema diagram and current-state feature/access documentation.
8. Run the validation listed below and resolve all failures before Step 2.

## Required tests

Add or update tests covering:

- migration backfill and reverse behavior;
- role uniqueness, replacement, and Standard derivation;
- any/all/include/exclude role query semantics;
- Player default query scope;
- staff access and non-staff denial/404 behavior for every Game Master surface and asset path;
- Hero deck validation and selection through the role helper;
- developer-data Version 1 adoption, Version 2 round trips, format rejection, role/pool coverage, and generated-lock compatibility;
- Card-tab edits, including multiple roles and Standard;
- Admin Catalog linked-card and suggestion-occurrence payloads and visible pool/role badges;
- gallery route/request serialization and Hero-excluded default;
- deck-builder Player/Hero and Player/non-Hero requests.

Do not run the prohibited service/integration test suites. Run the repository-approved targeted frontend tests plus lint, typecheck, Django checks, and direct artifact validation. At minimum:

Run the final Django command from `services/api`; run the `pnpm` commands from the repository root.

```text
pnpm --filter @card-reader/core lint
pnpm --filter @card-reader/core typecheck
pnpm --filter @card-reader/api lint
pnpm --filter @card-reader/api typecheck
pnpm --filter @card-reader/web lint
pnpm --filter @card-reader/web typecheck
pnpm --filter @card-reader/web test -- <affected specs>
uv run --project ../.. --package card-reader-api python manage.py check
```

Use `scripts/run-in-agent-env.py` for ad hoc Python checks as directed by `AGENTS.md`.

## Acceptance criteria

- All existing cards are Player cards after migration.
- Former Hero cards have exactly the Hero role; former non-Hero cards are Standard.
- A card can hold Hero, Boon, and Event simultaneously.
- `is_hero` is absent from the database and first-party writable contracts.
- Existing Hero-dependent deck, export, and Playtester behavior is unchanged.
- Staff can edit pool and multiple roles from the Card tab.
- Gallery filters can select/exclude Standard and each role; Hero is excluded by default.
- Admin Catalog linked cards and suggestion occurrences visibly identify their pool and every role, using Standard for an empty role set.
- Non-staff cannot list, retrieve, infer the existence of, or load images for Game Master cards.
- Staff can explicitly query and edit Game Master cards.
- Developer-data Version 2 round-trips pool and roles, while the pinned Version 1 bundle remains adoptable through the explicit compatibility adapter.
- No same-pool or mutually-exclusive-role database constraint has been introduced.
- Lint, typecheck, Django checks, affected frontend tests, schema diagram validation, and documentation validation pass.

## Explicit non-goals

- Automatic role inference during import.
- Import batch pool/role controls.
- The Player/Game Master sidenav toggle.
- New Game Master gameplay tools.
- A new card-to-card link model.
- Relaxing Game Master access beyond staff.
