# Card Classification Step 3.2: Admin-Owned Inference Rules

Status: implemented.

This checkpoint replaces template hints and hard-coded tag mappings with one admin-owned, pool-scoped rule catalog. Automatic import classification uses the tags and types actually detected on each card; exact batch overrides remain available independently for roles and factions.

The feature has not shipped, so this is a clean contract replacement. Do not retain runtime compatibility branches for template hints, inference policies 1-3, or legacy import-job classification snapshots.

## Outcome

Classification has two understandable paths:

- **Automatic:** union every enabled pool-specific rule whose Tag or Type was detected on the parsed card.
- **Override:** assign exactly the roles or factions selected for the batch, including an empty selection for Normal or No faction.

Roles and factions remain separate, multi-valued card facets. Their stable keys, labels, ordering, validation, filters, and special business behavior remain code-owned. Administrators own only the rules that translate detected metadata into those canonical values.

The Admin Catalog gains Card Roles and Card Factions sections. These sections show every supported definition, current card usage by pool, and the editable Tag/Type rules that infer it in Player, Evil, or Neutral.

## Locked decisions

- Remove template-based classification completely. Templates continue to configure parsing regions and extraction behavior, but no longer suggest roles or factions.
- Keep role and faction definitions code-owned. Admin users cannot create, rename, reorder, or delete canonical role/faction keys through the database.
- Make inference rules database-owned and staff-editable.
- Every rule targets exactly one pool, one role or faction, and one Tag or Type.
- Do not add an `all pools` or wildcard rule. Reusing a detector in several pools requires an explicit rule per pool.
- One Tag or Type may infer multiple roles and/or factions. A role or faction may be inferred by multiple Tags and Types.
- Automatic results are the canonical, deduplicated union of all matching enabled rules. There is no rule priority, first-match behavior, negative rule, or template contribution.
- Role and faction modes remain independent. A batch may override roles while factions remain automatic, or the reverse.
- Exact override bypasses every rule for that facet. An empty role override means Normal; an empty faction override means No faction.
- Pool remains an explicit batch choice and is never inferred.
- Rules affect future import processing only. Editing a rule does not retroactively rewrite existing cards.
- Existing-card safety remains unchanged: role mismatches preserve live roles and warn; a different inferred faction set resolves in a different pool-plus-faction identity namespace; targeted reparses remain ID-driven and preserve live classification.
- Tag and Type suggestions do not trigger rules until accepted into canonical Tag or Type records and subsequently detected on a parsed card.

## Domain model

Add a core-owned `CardClassificationRule` model with:

- `id`;
- `card_pool`: `player`, `evil`, or `neutral`;
- `target_kind`: `role` or `faction`;
- `target_key`: a canonical code-owned role/faction key, up to 64 characters;
- `source_kind`: `tag` or `type`;
- nullable `tag` and `type` foreign keys;
- `enabled`;
- normal timestamps.

Use explicit Tag and Type foreign keys instead of a generic foreign key or unvalidated JSON. Add database checks requiring exactly the source foreign key named by `source_kind` and requiring the other source to be null.

Add conditional unique constraints so the same `(pool, target kind, target key, source)` rule cannot be entered twice for either source kind. Add lookup indexes for enabled rules by pool and Tag/Type. The service layer validates `target_key` against the code-owned registry selected by `target_kind`; the database cannot provide that cross-code constraint.

Use `PROTECT` for Tag/Type deletion while classification rules reference the metadata entry. Return a useful conflict from Admin Catalog deletion that lists the affected role/faction and pool rules. Administrators must remove or repoint those rules before deleting the source metadata, preventing a catalog cleanup from silently changing future classification.

`CardRoleAssignment` and `CardFactionAssignment` remain unchanged. Do not convert them to foreign keys to the rule catalog, and do not make role/faction definitions database-owned as part of this checkpoint.

## Removing template and policy classification

Add a forward Django migration rather than rewriting the already-reviewed checkpoint migrations. Because the feature has not shipped, remove rather than deprecate:

- `Template.inferred_card_roles_json`;
- `Template.inferred_card_factions_json`;
- `ImportJob.template_role_snapshot_json`;
- `ImportJob.template_faction_snapshot_json`;
- `ImportJob.classification_inference_policy_version`;
- the policy 1/2/3 constants and hard-coded Tag-to-role/faction maps.

The migration also creates `CardClassificationRule`. Do not translate old template hints or hard-coded policy maps into compatibility rows. The authoritative initial rules come from reviewed catalog/developer data.

Do not allow an old queued or running job to silently continue under different semantics. The migration must preflight non-terminal import jobs and fail with a clear instruction to finish, cancel, or reset them before migrating. Completed/failed/cancelled history may remain, but the UI is not required to reinterpret its legacy evidence payload.

Remove template hint fields from template services, repositories, API serializers, seed/catalog inputs, developer-data records, template editor controls, tests, and documentation. Template selection remains required where the parser requires it; only its classification responsibility disappears.

## Rule snapshots and deterministic jobs

Admin ownership makes live configuration mutable, so an import job must snapshot the applicable rules at its authoritative creation boundary.

Replace the old template/policy fields with `ImportJob.classification_rule_snapshot_json`. Store a normalized object containing:

- snapshot schema version;
- selected card pool;
- enabled rules relevant to facets in automatic mode;
- for each rule: rule id, source kind, source metadata id and key, target kind, and target key;
- a stable digest of the canonical snapshot for audit and activity display.

The snapshot is immutable after job creation. Later rule edits, source label/key edits, retries, parser restarts, or grouped processing must not reinterpret an already-created job with new mappings. Metadata ids are the matching identity; source keys are retained only as human-readable evidence.

The core import creation operation loads and validates the rules inside the same authoritative transaction that creates the job. Upload prevalidation may report invalid configuration early, but the transaction owns the final snapshot. The creation fingerprint continues to represent the client's immutable request; server-derived rule state is captured on the created job and returned unchanged on idempotent replay.

Grouped reparses snapshot the same rules through the single Step 2.2 creation operation. Do not let template, maintenance, or parser callers construct rule snapshots independently.

## Classification engine and evidence

Replace the versioned policy classifier with a pure snapshot-driven classifier. It receives:

- the selected pool;
- independent role/faction modes and exact override arrays;
- the immutable rule snapshot;
- detected Tag ids/keys;
- detected Type ids/keys.

For each automatic facet, select snapshot rules matching a detected source id, union their targets, then normalize through the canonical role/faction registry. For each override facet, ignore the snapshot and normalize exactly the requested values.

The parser-job service already receives parsed `tag_ids` and `type_ids`; pass both into classification. Keep the parser dependent on core only and keep rule lookup/snapshot persistence out of parser-specific code.

Replace the current evidence contract with explicit rule evidence for each facet:

- mode: automatic or override;
- matched Tag sources;
- matched Type sources;
- matched rule ids and their pool/source/target details;
- exact override values when applicable;
- resolved values;
- the job snapshot digest.

Remove template hints and inference-policy versions from new evidence. Preserve the Step 2.2 distinction between pending, unavailable, resolved-empty, warning, and failed states. Automatic with no matching rules is a completed empty classification, not unavailable.

## Admin Catalog

Add a **Card classification** group to the existing Admin Catalog with two kinds:

- **Card Roles**;
- **Card Factions**.

Use names distinct from existing Deck Roles and Deck Types throughout route state and TypeScript contracts.

Each role/faction row is synthesized from the backend registry and includes:

- stable key, label, and rank;
- whether it is derived (Normal appears as explanatory derived state, not an editable role record);
- current linked-card counts split by accessible pool;
- configured rule count split by pool and source kind.

Selecting a canonical role or faction opens a rule editor. Show rules grouped by Player, Evil, and Neutral, with source-kind badges and the linked Tag/Type label and key. Staff can add, enable/disable, repoint, or remove a rule. The add form requires pool, source kind, and an existing Tag or Type selected by id. Duplicate combinations are rejected consistently by service validation and database constraints.

Normal is shown as a read-only derived explanation: it is produced when no roles resolve and cannot receive detector rules. No faction is likewise explanatory empty state rather than a persisted target or rule destination.

Enhance Tag and Type detail responses with reverse classification-rule references. Their Admin Catalog detail view shows which pool-specific roles/factions the entry can infer and links to the corresponding Card Role/Faction editor. Rule CRUD remains one shared API/service path regardless of which side initiated navigation.

Keep the Admin route and all Admin Catalog data global under Step 3.1. The active shell workspace must not filter catalog records, linked-card counts, suggestion occurrences, detail previews, searches, reverse references, or rules for another pool. Every authorized pool is visible together; pool is displayed as data and remains an explicit field in the rule editor.

## Core service and API ownership

Add a classification-rule repository under the existing metadata/catalog ownership or a focused classification package, whichever best matches the implementation after inspection. It owns rule queries, uniqueness checks, snapshots, reverse references, and persistence. A core service owns registry validation and CRUD transaction boundaries.

Extend `GET /admin/catalog` with the synthesized role/faction records and reverse rule summaries needed by the catalog list. Add focused staff-only endpoints for rule create/update/delete and detail rather than embedding mutation logic in the generic Tag/Type serializers.

Return typed conflicts for duplicate rules, protected source deletion, unsupported target keys, source-kind/FK disagreement, and inaccessible/unknown pools. API views translate those errors; they do not duplicate registry or rule validation.

The public `/cards/filters` endpoint continues to derive role/faction options from code-owned registries. Admin rule changes affect inference only and must not alter supported API values, filter ordering, or frontend classification types.

## Initial configuration

Store reviewed inference rules in developer data so clean environments reproduce admin-owned configuration. The initial configuration should express the agreed pool conventions without inventing unconfirmed metadata:

- Player: the canonical `hero` Tag infers Hero.
- Evil: canonical `boss` and `location` Tags infer Boss and Location; canonical `order`, `blood`, `dark`, and `metal` Tags infer their matching factions.
- Neutral: the canonical `shop-item` Tag infers Shop Item.

Add Boon, Event, or Type-based defaults only when the actual canonical Tag/Type keys are confirmed in the reviewed catalog. The Admin Catalog may add them immediately without a code release.

If a referenced source is absent from the reviewed catalog, developer-data validation fails rather than silently dropping the rule. No default rule is copied to all pools implicitly.

## Developer data

Bump the developer-data format to Version 5 because template records lose fields and the bundle gains classification rules.

- Remove `inferred_card_roles` and `inferred_card_factions` from `TemplateRecord`.
- Add a `classification_rules` collection using source natural keys: pool, target kind/key, source kind/key, and enabled state.
- Export rules in canonical pool/target/source order.
- During isolated import, resolve Tag/Type natural keys first, then create validated rules through the owning core service.
- Add coverage for required exact inference rules rather than required template hints.
- Update exporter, importer, isolated validation, doctor, round-trip tests, selection schema, and generated bundle tooling.

Because the classification feature is still undeployed, do not add a runtime compatibility adapter that preserves Version 4 template-hint semantics. Generate and validate a Version 5 development bundle through the normal tooling; never hand-edit `dev-data.lock.json`. The accepted Step 3.2 branch must bootstrap against the newly generated contract or explicitly document the external publish step blocking that bootstrap.

## Import and template UI

Keep the existing independent Automatic/Override controls for Roles and Factions, but simplify their copy:

- Automatic: “Use matching Tag and Type rules for this pool.”
- Override: “Use exactly these values for every card in this batch.”

Remove all template-hint previews and template-derived activity text. Import activity/details show the snapshot digest/rule count and per-item matched Tag/Type evidence. Use shared card role/faction formatters and Admin Catalog links where appropriate.

Remove role/faction controls from the Template editor and its frontend/API types. Template selection remains in the import form for parsing, but changing templates no longer changes classification except indirectly when a different parser configuration detects different Tags or Types on the image.

## Stateful workflow boundaries

The authoritative success condition for rule mutation is a committed, validated `CardClassificationRule` row returned by the core service. Catalog refresh and toast rendering are independent frontend follow-up work and cannot reverse a confirmed mutation.

The import idempotency boundary remains the Step 2.2 job creation key and immutable request payload. Rule snapshot creation is part of that same server transaction. Upload cleanup, cancellation, parser claim/process behavior, and post-success notification cleanup retain their existing independent failure semantics.

Rule edits do not mutate already-created snapshots. Repeating or retrying an existing creation key returns the original job and snapshot; creating a new job after a rule edit receives the new snapshot.

## Documentation updates after implementation

Update current-state documentation only after behavior exists:

- `docs/imports-and-parsing.md` for rule-based automatic classification and exact overrides;
- `docs/card-management.md` for code-owned definitions versus admin-owned inference rules;
- `docs/developer-data.md` for Version 5 rules and removed template hints;
- Admin/catalog guidance where applicable;
- `docs/card-database-diagram.svg` for `CardClassificationRule` and its Tag/Type relationships.

Add amendment notes to Steps 2 and 2.3 explaining that Step 3.2 supersedes their template-hint and code-policy portions; retain those documents as an accurate record of the incremental implementation history.

## Implementation sequence

1. Merge Step 3.1 into `feature/card-classification` and branch `feature/card-classification-step-3-2-admin-owned-inference-rules` from the updated umbrella branch.
2. Commit this approved plan/AGENTS guidance separately and open the checkpoint PR against `feature/card-classification` when implementation is ready for review.
3. Add the rule model, constraints, indexes, non-terminal-job preflight, and field-removal migration.
4. Add the core rule repository/service, registry validation, reverse lookups, snapshot normalization, and typed errors.
5. Replace versioned/template classification with the snapshot-driven Tag/Type classifier and evidence contract.
6. Update authoritative import creation, grouped reparses, parser-job processing, serializers, activity refresh, and mismatch behavior.
7. Remove template classification fields and UI across core, API, frontend, tests, and schemas.
8. Add Admin Catalog role/faction records, rule CRUD, reverse Tag/Type references, and staff-only API authorization.
9. Add frontend Card Roles/Card Factions catalog sections and the shared pool/source rule editor in both themes.
10. Add developer-data Version 5 rules, coverage, exporter/importer/doctor behavior, and reviewed initial configuration.
11. Update the current-state docs and database diagram.
12. Run permitted validation, open a non-draft PR to the umbrella, and nurture CI and automatic Codex review until clear. Do not merge without the user’s direction.

## Required tests

### Schema and rule service

- source-kind/FK check constraints for Tag and Type rules;
- conditional uniqueness per pool/target/source;
- the same source mapping to several targets and pools;
- unsupported pool, target kind, and target key rejection;
- protected Tag/Type deletion with useful conflict details;
- enabled/disabled rule queries and canonical ordering;
- migration preflight for non-terminal jobs and removal of old template/policy fields.

### Classification

- Tag-only, Type-only, and combined automatic inference;
- one source inferring multiple targets and several sources inferring one target;
- exact pool scoping with no wildcard or cross-pool leakage;
- canonical deduplication and multi-role/multi-faction results;
- independent role override, faction override, both overrides, forced Normal, and forced No faction;
- disabled and unmatched rules producing explicit resolved-empty evidence;
- evidence containing matched Tag/Type sources, rule targets, resolved values, and snapshot digest;
- no template values or live rule queries influencing classification.

### Job stability and identity

- rule edits after job creation not changing queued/retried results;
- idempotent replay returning the original immutable snapshot;
- new creation keys observing newly committed rules;
- grouped reparses using the shared snapshot operation;
- role mismatch warnings preserving live roles;
- faction inference preceding pool-plus-faction name/alias/hash lookup;
- same-name cards remaining independent across exact faction namespaces;
- targeted reparses preserving live pool, roles, and factions.

### Admin/API/frontend

- staff-only rule CRUD and catalog visibility;
- canonical roles/factions displayed but not creatable/deletable;
- Normal and No faction displayed as non-targetable derived states;
- role/faction usage and rule counts split by pool;
- add/edit/disable/delete flows for Tag and Type sources;
- reverse rule references on Tag and Type details;
- duplicate/protected/invalid errors rendered clearly;
- Import form/activity no longer showing template hints and accurately presenting automatic versus exact behavior;
- visible Admin Catalog and Import UI in light and dark themes.

### Developer data and documentation

- Version 5 schema rejects template hint fields and invalid/dangling rules;
- rule export/import canonical round trip;
- clean import resolves Tag/Type keys before rule creation;
- doctor and coverage require the reviewed rule set;
- database diagram remains valid SVG XML;
- no runtime references to removed template snapshots, policy versions, or hard-coded mappings remain.

Do not run prohibited service/integration suites. Run targeted core and API tests, affected frontend tests, core/API/parser/web lint and typecheck, Django checks, migration drift checks, developer-data isolated validation, and SVG XML validation.

## Acceptance criteria

- New imports have only Automatic metadata-rule classification or exact per-facet override.
- Templates contain no role/faction hints in the database, API, UI, job snapshots, or developer data.
- No hard-coded Tag-to-role/faction policy remains in runtime code.
- Admin Catalog displays every canonical Card Role and Card Faction and allows staff to manage pool-specific Tag and Type rules.
- Admin Catalog returns the same authorized all-pools records, counts, previews, and rules in every shell workspace.
- Rules are explicit per pool and never leak across Player, Evil, or Neutral.
- One detected Tag/Type can infer several values and automatic results union deterministically.
- Immutable job snapshots make queued processing and retries independent of later admin edits.
- Existing-card, faction-identity, targeted-reparse, warning, upload, and cleanup semantics remain intact.
- Role/faction definitions, filters, API values, and special behavior remain code-owned and type-safe.
- Developer data reproduces the reviewed rule catalog on a clean checkout.
- Required tests, lint, typecheck, checks, artifact validation, documentation, CI, and automatic review are clear.

## Explicit non-goals

- Making role or faction definitions fully database-created or user-defined.
- Inferring card pool.
- Template-based classification of any kind.
- Rule priority, negative/exclusion rules, regex expressions, arbitrary predicates, or conditional combinations of metadata.
- Automatic classification from symbols, keywords, OCR text, card names, or artwork in this checkpoint.
- Retroactively reclassifying existing cards when a rule changes.
- Pool-to-role/faction validity constraints in the database.
- Neutral overlays, mixed-pool ordinary galleries, deck classification, scenarios, or Evil/Neutral Playtester behavior.
