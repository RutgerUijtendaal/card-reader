# Card Classification Step 2.3: Faction Classification

Status: proposed implementation plan and active design checkpoint. Step 2.2 is merged into the classification umbrella branch. [Step 3](card-classification-step-3-card-pool-workspaces.md) remains blocked until this checkpoint is approved, implemented, validated, reviewed, and merged.

This checkpoint completes the card-classification vocabulary before the Player/Evil/Neutral workspace is built:

1. [Card classification foundation](card-classification-step-1-foundation.md)
2. [Authorization seam consolidation](card-classification-step-1-1-authorization-seam.md)
3. [Import inference](card-classification-step-2-import-inference.md)
4. [Pool-scoped card identity](card-classification-step-2-1-pool-scoped-identity.md)
5. [Import workflow seam consolidation](card-classification-step-2-2-import-workflow-seam.md)
6. Faction classification (this document)
7. [Player, Evil, and Neutral workspaces](card-classification-step-3-card-pool-workspaces.md)

## Outcome

Add **Faction** as a second multi-valued, code-owned card-classification facet. Factions use their own persisted assignments and public fields, while reusing the reliable classification mechanics already established for roles: template hints, stable-tag inference, batch overrides, immutable job snapshots, explainable evidence, mismatch warnings, manual editing, filters, Admin Catalog badges, and developer-data round trips.

After this step, card classification has three deliberately different dimensions:

- `card_pool`: exactly one of Player, Evil, or Neutral; it owns identity scoping and authorization;
- `card_roles`: zero or more structural/gameplay roles such as Hero, Boss, Location, Boon, Event, and Shop Item;
- `card_factions`: zero or more affinities: Order, Blood, and Darkness; the exact canonical faction set participates in natural card identity inside a pool.

The implementation must generalize the shared role workflow into a small classification-facet seam without turning persistence or public contracts into an untyped arbitrary-property system.

## Locked decisions

- Faction is not a role, symbol, tag, or pool. It is a separate card-level dimension.
- Factions are multi-valued from the start, even if most initial cards have exactly one.
- Faction keys are code-owned and use 64-character-capable storage. The initial ordered values are **Order** (`order`), **Blood** (`blood`), and **Darkness** (`darkness`).
- The ordered role registry becomes **Hero** (`hero`), **Boss** (`boss`), **Location** (`location`), **Boon** (`boon`), **Event** (`event`), and **Shop Item** (`shop_item`). Hero remains the only role with existing deck-builder and Playtester behavior; the other roles remain descriptive until their own gameplay rules are designed.
- **Normal** is the product label for the existing derived empty-role state. It is never persisted. Keep the existing `standard` transport/filter sentinel because it already represents that derived query and is not domain data.
- Factions do not affect whether a card is Normal. An Evil card with no roles and the Blood faction is displayed as Normal + Blood.
- The intended initial conventions are Player cards as Normal or Hero, Evil cards as Normal/Boss/Location with optional factions, and Neutral cards as Normal/Boon/Event/Shop Item. These are code-owned presentation/applicability metadata, not database constraints.
- Do not reject a role or faction solely because it is unusual for the selected pool. Cross-pool relationships and future rules may need those combinations, and no deployed evidence justifies a hard validity constraint.
- Gallery role and faction options remain unconditional. Pool-aware, count-aware, and context-sensitive facets stay deferred to the full filter redesign.
- Automatic role inference and automatic faction inference are independent. Either facet may be switched to an exact batch override without disabling inference for the other facet.
- An empty role override forces Normal. An empty faction override forces no faction.
- Templates may declare both inferred roles and inferred factions. Import inference unions template hints with stable tag mappings within each automatic facet.
- Existing card classification remains authoritative after identity resolution in the same pool and exact faction namespace. Imports warn but never silently replace stored roles or factions.
- Manual Card-tab edits remain authoritative and can change pool, roles, and factions in one card-level operation.
- Natural card identity is scoped by pool plus the exact canonical faction set. The same normalized name, alias, or image hash may identify separate cards in different faction namespaces.
- A multi-faction card belongs to one namespace representing its complete canonical faction set. A factionless card belongs to an explicit empty-faction namespace. Partial overlap does not make two faction sets identical.
- Roles never participate in identity matching. Two cards with the same pool, faction set, and normalized name cannot coexist merely because their roles differ.
- Faction edits are identity moves. Name, pool, and faction edits must validate and commit against the complete destination namespace atomically.
- Do not model faction as mana or symbol metadata in this checkpoint. A later gameplay pass may relate factions to resource mechanics without changing card classification ownership.

## Authoritative success and failure domains

Step 2.2's import lifecycle remains authoritative. Adding factions must not reopen upload admission, idempotency, cleanup, cancellation, polling, or grouped-reparse transaction boundaries.

Creating an import job and all initial items with immutable pool, role, faction, template, and inference-policy snapshots remains the authoritative upload success condition. The creation fingerprint includes both facet modes and overrides so the same creation key cannot reconcile two different classification requests.

For parser persistence, one transaction owns:

- the card/version result;
- new-card role and faction assignments;
- resolved role and faction audit values;
- structured classification evidence;
- classification mismatch warnings;
- the terminal completed item state.

Post-success notifications and frontend refresh remain independent failure domains and cannot rewrite committed parser success.

## Domain model and registries

### Roles

Extend the core-owned role registry with Boss and Shop Item. Keep canonical keys, labels, ranks, model choices, normalization, validation, filter metadata, and display ordering derived from that registry.

Extend the typed frontend role registry rather than adding feature-local options or labels. Every role surface must continue consuming that single cards-domain registry.

The existing derived `standard` filter value remains rank 0 but is labeled **Normal**. Persisted role ranks start at 1 in this order: Hero, Boss, Location, Boon, Event, Shop Item.

### Factions

Add a core-owned faction registry parallel to the role registry. It owns:

- typed keys and labels;
- canonical Order, Blood, Darkness ordering and ranks;
- Django field choices;
- normalization and validation;
- filter metadata;
- template/import/developer-data validation.

Add one typed cards-domain frontend faction registry and shared formatters. Import, editor, Gallery, template administration, and catalog code consume it instead of maintaining local option lists.

### Shared classification mechanics

Introduce a narrow internal abstraction for mechanics common to roles and factions: canonical value ordering, automatic/override resolution, template/tag evidence, exact overrides, and evidence presentation. The abstraction is parameterized by an explicit facet definition; callers still receive typed role and faction results.

Do not create a generic database assignment table, generic `card_classifications` API object, runtime-configurable facet registry, or arbitrary JSON bag. Role and faction storage, query fields, and public payloads remain explicit.

## Database migration

Add a new reversible Django migration after the current umbrella schema state:

- create `CardFactionAssignment` with UUID/text identity, `card_id`, `faction`, timestamps, a faction index, and `UniqueConstraint(card, faction)`;
- store faction values in a 64-character choices-backed field;
- add a non-editable `faction_identity_key` to `Card` and `CardAlias`, derived from the complete canonically ordered faction set;
- backfill existing cards and aliases into the empty-faction namespace;
- replace `UniqueConstraint(card_pool, key)` on cards and aliases with `UniqueConstraint(card_pool, faction_identity_key, key)` while keeping the key and namespace lookup paths indexed;
- add `Template.inferred_card_factions_json`, defaulting to an empty array;
- add independent faction mode, override, and template-snapshot fields to `ImportJob`;
- rename `card_role_inference_policy_version` to `classification_inference_policy_version` while preserving existing values;
- add resolved faction and target-faction snapshot arrays to `ImportJobItem`;
- replace the flat role-only evidence field with a structured classification-evidence field that contains explicit `roles` and `factions` sections.

The identity key uses a deterministic, collision-free serialization of the complete canonical faction list rather than a lossy hash. Application callers never supply it directly; the cards identity repository calculates it from normalized faction values.

`CardFactionAssignment` rows and `faction_identity_key` form one identity invariant. Runtime code must not mutate faction assignments directly: creation, replacement, and removal go through the cards identity seam, which updates the assignments plus the card and alias namespace keys in one transaction.

Migrate existing role evidence into the `roles` section and add an empty faction section. Reversal restores the prior role evidence and policy-version field and must reject data that cannot be represented safely rather than silently dropping faction assignments or evidence. Before restoring Step 2.1's pool-only uniqueness, reversal must also reject cross-faction duplicate primary/alias keys and cross-table primary/alias collisions.

No migration assigns factions from existing card tags. Only newly processed automatic imports use the new policy. Staff can deliberately reparse or edit older cards.

Update [the database diagram](card-database-diagram.svg) with `CardFactionAssignment`, the template faction hints, and the import snapshot/evidence fields.

## Classification inference policy

Rename the code-owned import policy concept from card-role inference to card-classification inference. Preserve policy versions 1 and 2 exactly for queued/retryable jobs and introduce policy version 3 for new work.

Policy version 3 contains these exact normalized tag mappings:

| Stable tag key | Facet | Value |
| --- | --- | --- |
| `hero` | role | `hero` |
| `boss` | role | `boss` |
| `location` | role | `location` |
| `shop-item` | role | `shop_item` |
| `order` | faction | `order` |
| `blood` | faction | `blood` |
| `darkness` | faction | `darkness` |

Boon and Event continue to be inferable from template hints. Templates may also hint Boss, Location, Shop Item, or any faction. Do not infer from localized labels, free text, card names, pool, or hard-coded template IDs.

Automatic resolution runs independently per facet:

```text
resolved roles = template role hints union tag-derived roles
resolved factions = template faction hints union tag-derived factions
```

An exact role override replaces only automatic role inference. An exact faction override replaces only automatic faction inference. Evidence records the mode, template values, all matched stable tag keys, mapped values, override values, and resolved values for each facet.

Unknown policy versions fail explicitly. Retry copies the original snapshots and policy version byte-for-byte; a new explicit import or reparse snapshots the current policy.

## Templates and catalog inputs

Add `inferred_card_factions` beside `inferred_card_roles` in template services, serializers, seeds/catalog inputs, developer data, and the template admin editor. Both arrays are normalized, deduplicated, canonically ordered, and validated against their owning registries.

Add or verify the stable catalog tag keys used by policy version 3. Do not create localized-label aliases in classification code. A missing expected stable tag or required template hint must be visible through developer-data coverage/doctor checks rather than silently changing imports to Normal or no faction.

Template role and faction hints remain small configuration payloads and are not gallery query dimensions; JSON fields remain appropriate for them.

## Faction-scoped card identity

Extend the cards-repository identity seam established by Step 2.1. Every natural-key operation requires an explicit pool and complete canonical faction set:

- primary-name and alias resolution;
- untargeted latest-image-hash matching;
- primary and alias conflict detection;
- race-safe card creation;
- alias creation and transfer;
- rename, pool move, and faction move;
- merge preview and execution.

IDs remain globally stable and continue to own URLs and relationships. The faction identity key is an internal constraint/lookup value, not a replacement external identity.

A simultaneous name, pool, role, and faction edit is one transaction. Calculate the destination pool, destination faction namespace, resulting primary key, current aliases, and newly preserved old-name alias; validate the complete destination namespace before updating the card, aliases, role assignments, or faction assignments. Any collision rolls the entire edit back.

Same-pool cards in different faction namespaces are intentionally distinct. Merge operations therefore require the same pool and same exact faction set; staff must explicitly reclassify a card first if a cross-faction merge is genuinely intended. Same-namespace merge alias transfer preserves the target pool and faction identity key.

## Import jobs, reparses, and persistence

### Job creation and fingerprints

Extend the Step 2.2 core creation input with:

- `card_faction_mode` (`automatic` or `override`);
- normalized `card_faction_override`;
- the selected template's faction snapshot;
- the shared classification inference-policy version.

The normalized creation fingerprint includes role mode/override and faction mode/override independently. Prevalidation and transactional creation use the same shared normalizer so admission cannot accept a payload the authoritative operation rejects.

For untargeted imports, classification must resolve the complete faction set before natural identity lookup. Primary names, aliases, and latest-image hashes are then searched only inside the selected pool and resolved faction namespace. Use the `(card_pool, faction_identity_key, key)` constraints for race-safe creation; a concurrent loser resolves the winner in that exact namespace or receives the typed identity conflict.

### Item evidence and warnings

Import list/detail payloads expose:

- resolved roles and resolved factions;
- nested role and faction inference evidence;
- target pool, role, and faction snapshots;
- the existing ordered warning collection.

Keep one stable `card_classification_mismatch` warning. Its details include `card_pool`, `card_roles`, and `card_factions` for inferred, existing, queued, and live states as applicable. An untargeted role difference triggers the warning only after a same-pool, same-faction identity match. A same-name or same-image card in another pool or faction namespace is an independent identity and produces no mismatch warning. Targeted reparses remain ID-driven and may warn when queued or inferred factions differ from the live target without resolving a different card.

Pending, resolved, warning, and unavailable evidence states continue to derive from explicit item status and persisted evidence. An empty role result is Normal only after classification ran; an empty faction result is shown as No faction only after classification ran.

### New and existing cards

- New untargeted card: persist pool, role assignments, and faction assignments atomically with identity/version creation.
- Existing card resolved in the same pool and exact faction namespace with matching roles: append the parsed version normally.
- Existing card resolved in the same pool and exact faction namespace with different roles: append the valid version, preserve live roles, and complete with the mismatch warning.
- Same name, alias, or image hash in another faction namespace: create or resolve an independent card; do not treat the faction difference as a classification mismatch.
- Targeted reparse: never rewrites pool, roles, or factions; preserve queued and live snapshots in evidence and warn on differences.

### Grouped reparses

Expand the Step 2.2 grouped-reparse key to `(template, pool, canonical roles, canonical factions)`. Every target also stores its own pool, role, and faction snapshots. Template and maintenance callers continue to use the single transactional grouped-reparse operation and must not recreate their own grouping or job loops.

## Card editing, querying, and API contracts

Add explicit `card_factions` arrays to card summaries, details, search records, embedded card payloads, groups, catalog links, and other card-derived contracts that already expose pool and roles.

The Card tab edits pool, roles, and factions. One save may change all three and uses the expanded atomic card edit/identity move boundary. A faction change recalculates the card and alias faction identity keys, validates the destination namespace, and preserves versions, groups, decks, redirects, and all other relationships.

Add faction query parameters parallel to roles:

- `card_factions`;
- `card_faction_exclude`;
- `card_faction_match=any|all`.

Add `card_factions` metadata to `GET /cards/filters` in canonical order. Export and grouped-gallery consumers that accept card filters must use the same repository query seam. Do not introduce pool-aware option pruning or result-count facets in this checkpoint.

Public role contracts additionally accept `boss` and `shop_item`. The `standard` filter sentinel remains accepted and is presented as Normal.

Public natural-key behavior changes: normalized card and alias keys are unique within `(card_pool, exact card_factions set)`, not within `card_pool` alone. External consumers must continue using card IDs as global identity and must include the explicit faction set when invoking any internal natural-key lookup.

## Frontend surfaces

Extend the cards domain with explicit faction types, options, guards, labels, and display helpers. Add shared facet-level UI helpers only where roles and factions genuinely have the same interaction; do not collapse their domain types into `string`.

Update these surfaces:

- Card editor: separate Role and Faction multi-select groups; show Normal for no roles and No faction for no factions.
- Import setup: independent Automatic/Override controls for roles and factions, both reset to Automatic after confirmed or reconciled creation.
- Import activity/detail: render role and faction evidence and mismatch comparisons from the nested evidence contract.
- Template admin: separate inferred-role and inferred-faction controls.
- Gallery filters and route state: independent include/exclude/match controls for factions; keep all faction choices available in every pool for now.
- Admin Catalog and linked-card/search rows: retain the pool badge and render role and faction badges as visually distinct groups so duplicate names remain understandable.

Hero remains excluded by default. Do not add default faction exclusions. Verify all changed surfaces in light and dark themes.

## Developer data

Bump newly generated developer-data bundles from format Version 3 to Version 4 because cards and templates gain faction fields.

- `CardRecord` gains `card_factions`.
- `TemplateRecord` gains `inferred_card_factions`.
- coverage gains `min_cards_by_faction`, defaulting each code-owned faction to zero.
- template coverage gains `required_template_faction_hints`.
- Version 1-3 adoption supplies empty card/template factions while retaining existing pool and role adoption behavior.
- export, isolated import validation, import, doctor, and round-trip tests cover multi-faction cards and template hints.
- public archives remain Player-only; a Player record with a faction is still valid because pool/faction conventions are not hard constraints;
- card and alias identity keys are reconstructed from each record's canonical factions during import rather than serialized as user-owned bundle fields.

Do not regenerate or hand-edit `dev-data.lock.json` as part of implementation. Publishing a real Version 4 bundle remains a separate production operation.

## Delivery and implementation sequence

- Merge Step 2.2 into `feature/card-classification` before branching this checkpoint.
- Create `feature/card-classification-step-2-3-faction-classification` from the updated umbrella branch.
- Open the Step 2.3 PR against `feature/card-classification`, not `master`; keep the aggregate feature PR open.
- Keep documentation as the first commit, then implement in focused commits and batch pushes for automatic review.

Implementation order:

1. Add backend role/faction registries, model fields/assignment table, faction identity keys, pool/faction/key constraints, and the reversible migration.
2. Generalize the core classifier and evidence types, preserve v1/v2 behavior, and add policy v3.
3. Extend template services/APIs and catalog inputs with faction hints and the new roles.
4. Extend the Step 2.2 creation operation, fingerprint, import snapshots, serializers, and grouped reparses.
5. Extend the cards identity seam for pool-plus-faction namespaces, then persist and compare both facets atomically in card writes, edits, mismatch warnings, merges, and targeted reparses.
6. Add faction repository filters, filter metadata, exports, and all card-derived API payloads.
7. Add developer-data Version 4 schemas, adapters, coverage, exporter/importer, and doctor behavior.
8. Add the frontend registries, editor, import, template, Gallery, route, and Admin Catalog surfaces.
9. Update current-state card management, imports, developer-data, API/access documentation where affected, and the database diagram.
10. Run permitted validation, nurture the checkpoint PR until clear, merge it into the umbrella, then branch Step 3 from the updated umbrella.

## Required tests

### Schema and registries

- faction field length, choices, canonical order, assignment uniqueness, cascade behavior, deterministic namespace keys, per-namespace uniqueness, and guarded reversible migration;
- primary/alias and alias/alias collisions are blocked inside one pool/faction namespace and allowed across different faction namespaces;
- simultaneous name/pool/faction moves update every alias and roll back completely when the destination namespace conflicts;
- Boss and Shop Item role normalization/ordering;
- role and faction registries drive choices, serializers, filter metadata, and frontend options;
- Normal remains derived from an empty role set even when factions exist.

### Inference and templates

- policy v1 remains Hero-only and policy v2 remains Hero/Location-only with no faction inference;
- policy v3 infers Hero, Boss, Location, Shop Item, Order, Blood, and Darkness from their exact stable tags;
- template-only, tag-only, combined, duplicate, and multi-value inference for each facet;
- independent role override, independent faction override, both overrides, forced Normal, and forced no-faction cases;
- queued/retry snapshot isolation across later template and policy edits;
- template API, seed/catalog, validation, and admin round trips for both hint arrays.

### Import workflows

- creation fingerprint changes for either facet mode or override and replays exact payloads only;
- new-card role/faction assignment and existing-card exact match;
- role-only and targeted queued/live classification mismatches preserve live classification and complete with one structured warning;
- same-name, same-alias, same-image, and different-art cards remain independent across pools and exact faction namespaces without mismatch warnings;
- faction inference completes before untargeted identity resolution, and concurrent same-namespace creation resolves one winner;
- grouped reparses split on roles or factions and remain all-or-nothing;
- pending/empty/unavailable evidence is explicit for both facets;
- Step 2.2 upload cleanup, cancellation, polling, and terminal-status matrices remain green.

### Queries, APIs, and UI

- faction include, exclude, any/all matching, combinations with role filters, and export/grouped-gallery parity;
- `/cards/filters` returns Normal, all roles, and all factions in canonical order from backend registries;
- card edit adds/removes multiple factions, atomically combines a pool/name/role/faction edit, updates aliases, and rolls back on destination-namespace conflicts;
- same-namespace merges transfer aliases and cross-faction merges are rejected until explicitly reclassified;
- summaries, details, embedded cards, catalog links, groups, decks, and notifications expose factions without changing authorization scope;
- all role and faction surfaces consume their shared frontend registries;
- import, editor, template, Gallery, route, and Admin Catalog interactions render correctly in light and dark themes.

### Developer data and documentation

- Version 1-3 adoption supplies empty faction fields and Version 4 round-trips multi-faction cards/templates;
- Player-only selection and archive validation remain pool-scoped when cross-pool twins exist;
- coverage and doctor checks validate required factions and template hints;
- database-diagram SVG remains valid XML and current-state documentation matches the shipped contract.

## Validation

Run targeted core and API tests only; do not run prohibited service/integration suites locally. Run affected frontend tests, Django `check`, migration drift checks, core/API/parser/web lint and typecheck, developer-data schema/round-trip validation, and SVG XML validation. Verify changed visible UI in both light and dark themes.

## Acceptance criteria

- Faction is a first-class, multi-valued card dimension with Order, Blood, and Darkness.
- Pool plus the exact canonical faction set scopes names, aliases, untargeted image matching, creation races, and merge eligibility, allowing same-name cards in different factions.
- Boss and Shop Item complete the agreed initial role vocabulary.
- Roles and factions share mechanics without sharing persistence or losing static typing.
- Automatic inference, exact overrides, template hints, evidence, mismatch warnings, reparses, and manual edits work independently for both facets.
- Import creation and parser completion retain the authoritative success and cleanup semantics established by Step 2.2.
- API queries, Gallery filters, card/editor payloads, Admin Catalog badges, and developer data expose factions consistently.
- No pool/faction hard constraint or implicit Neutral/other-pool mixing is introduced.
- Existing Hero deck-builder and Playtester behavior remains unchanged.
- All permitted validation and automatic review are clear before Step 2.3 merges into the umbrella branch.

## Explicit non-goals

- Pool-aware or count-aware filter option pruning.
- User-defined roles, factions, or arbitrary classification facets.
- Faction-specific gameplay, resources, mana rules, symbols, icons, deck constraints, or scenario logic.
- A requirement that every Evil card has a faction or exactly one faction.
- Database enforcement that factions belong only to Evil cards or that roles belong only to their conventional pools.
- Deck pool classification, Evil/Neutral deck building, scenario persistence, or Neutral overlays.
- Step 3 sidenav/workspace behavior.
