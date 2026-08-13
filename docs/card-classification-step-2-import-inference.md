# Card Classification Step 2: Import Inference

Status: implemented by the Step 2 checkpoint; retained as the executable design and acceptance record.

Target amendment: this document records Step 2's temporary Player/Game Master import values. [Step 2.1](card-classification-step-2-1-pool-scoped-identity.md) replaces `game_master` with `evil` and `neutral`, requires one of the final three pools for every batch, and keeps inference and override semantics unchanged.

Faction amendment: [Step 2.3](card-classification-step-2-3-faction-classification.md) adds an independent faction facet, generalizes the role-shaped inference/evidence machinery, and requires untargeted imports to resolve factions before natural identity lookup. This document remains the implementation record for the original role-only policy versions.

This step adds reliable, explainable import classification on top of the pool and role model. It must not reintroduce Hero-specific persistence or allow an import to silently reclassify an existing card.

## Outcome

Every import batch selects exactly one card pool and defaults to automatic role inference. Automatic inference unions roles declared by the selected template with roles inferred from parsed metadata. Staff can instead choose an explicit batch-wide role override, including forced Standard.

New cards receive the batch pool and resolved roles. Once an existing identity is resolved, it is updated only when its stored classification agrees; a mismatch completes with a durable warning and preserves the existing card classification for manual review in the Card tab. [Step 2.1](card-classification-step-2-1-pool-scoped-identity.md) makes that identity resolution pool-scoped so a same-name card in the other pool is a distinct card rather than a mismatch.

## Locked decisions

- Card pool is always an explicit batch choice. It is not inferred from roles or template.
- Role mode is either `automatic` or `override`; automatic is the default.
- Overrides are complete batch-wide role sets, not additions to inferred roles.
- An empty override means intentionally force Standard.
- Automatic inference unions all matching signals and therefore supports multiple roles.
- The stable tag keys `hero` and `location` infer the Hero and Location roles under inference policy version 2. Do not infer from localized labels or free text when a matched tag key is available.
- Templates declare zero or more inferred role hints. The inference engine is generic and must not hard-code individual template IDs.
- No inferred role means Standard; Standard is never stored as a role.
- Existing card classification is authoritative after identity resolution. Import mismatches warn and preserve it; imports never silently move an existing card between pools or replace its roles. Step 2.1 requires untargeted identity resolution to stay inside the selected pool.
- Manual Card-tab edits remain authoritative after import.
- Inference is core-owned and consumes normalized evidence. Parser code extracts evidence but does not own classification policy.
- Upload creation is idempotent through a stable client-generated creation key. An ambiguous response must be reconcilable without creating a second job, upload directory, content version, or set of parser items.
- Queued work snapshots a versioned inference policy as well as template hints. Deploying a new tag-to-role rule must not reinterpret an existing job or retry.
- Import items own an ordered collection of warnings. Lifecycle, classification, and future warnings may coexist; no workflow may overwrite an unrelated warning.
- System-generated reparses snapshot the target classification per item and never depend on `CardVersion` having originating-job lineage.

## Authoritative success and failure domains

Creating the `ImportJob` and all of its items with an immutable pool, role mode, override payload, inference-policy version, and creation key is the authoritative success condition for the upload mutation. Browser cleanup or navigation failures must not undo a confirmed job creation.

`POST /imports/upload` is an idempotent create operation. The browser generates one UUID creation key for a concrete submit payload and retains that key plus the exact files and form values until success is confirmed or the user explicitly abandons/edits the attempt. Before creating an application upload directory, the server computes a normalized request fingerprint containing the template, content-version inputs, classification inputs, ordered file names, sizes, and content checksums. Application upload storage uses the creation key as its stable namespace. Each source file is written and checksum-verified at a unique staging path, then published to its final name with an atomic create-only operation so an interrupted or concurrent request can never expose a partial final file.

- The first request creates the upload directory, content version, job, and items once and returns `201`.
- Replaying the same key and fingerprint returns the existing job with `idempotent_replay=true`; it does not enqueue work again.
- Reusing a key with a different fingerprint returns `409`.
- An authenticated creation-key lookup lets the browser reconcile a lost response. A found job confirms success; a definitive miss permits retry with the same locked payload and key.
- Matching replays return before writing a second application upload directory. Orphan cleanup after an uncommitted first attempt is an independent failure domain and must not reverse or hide a later confirmed job.

The upload, durable job creation, parser execution, classification resolution, card persistence, and post-processing UI refresh are independent failure domains. A completed parser item with a classification mismatch remains completed-with-warning; the warning must not roll back an otherwise valid parsed version.

Retries reuse the exact job and item classification snapshots. Reparses create new immutable snapshots from their explicit target cards as described below. Later template edits or inference-policy deployments must not change the meaning of already queued or retryable work.

## Data model

Implement typed, explicit fields rather than hiding classification inside the existing free-form `options_json`.

### Template

Add `Template.inferred_card_roles_json`, a validated JSON array of role keys. JSON is appropriate here because the value is a small configuration payload and is not used as a gallery query dimension.

Expose it as `inferred_card_roles` in template API contracts and add multi-select controls to `frontend/src/features/admin/views/TemplatesAdminView.vue`. Template serializers and the core template service must normalize, deduplicate, sort, and validate the array against code-owned roles.

Carry template role hints through seeds and developer data:

- add the hints to `seed-templates.json` and template seeding/update behavior;
- add `inferred_card_roles` to the developer-data `TemplateRecord`, exporter, importer, and isolated validation;
- bump the developer-data format from Version 2 to Version 3 for newly generated bundles;
- keep explicit Version 1 and Version 2 adapters, with missing template hints normalized to an empty set;
- publish and validate a Version 3 bundle before replacing `dev-data.lock.json`; never fabricate the bundle checksum locally;
- add coverage or doctor validation for every template that is expected to infer a role, so a missing Boon/Event/Location hint cannot silently turn imported cards into Standard after bootstrap.

### Import job

Add required fields to `ImportJob`:

- `creation_key`, unique and immutable; API uploads receive it from the browser and internal workflows generate one server-side;
- `creation_fingerprint`, covering the normalized create payload and ordered file content;
- `card_pool`;
- `card_role_mode`, with `automatic` and `override` values;
- `card_role_override_json`, a normalized role array used only in override mode;
- `template_role_snapshot_json`, capturing the selected template's role hints at job creation;
- `card_role_inference_policy_version`, selecting an immutable code-owned inference-policy implementation.

Validation rules:

- automatic mode requires an empty override array;
- override mode accepts zero or more roles; zero means forced Standard;
- every role must be code-owned;
- the pool is always explicit and valid;
- creation keys are unique and a replay must match the stored fingerprint;
- the inference-policy version must be supported by the running classifier.

The template snapshot and policy version make queued work deterministic even if staff edit the template or a release changes tag inference before the parser processes the job. Keep old policy implementations available while jobs using them remain retryable; do not silently dispatch an unknown version through the latest policy.

### Import item

Add audit fields to `ImportJobItem`:

- `resolved_card_roles_json` for the automatic or overridden result;
- `card_role_inference_json` for structured evidence such as template hints and matched tag keys;
- `target_card_pool_snapshot` and `target_card_roles_snapshot_json` for targeted reparses;
- `warnings_json`, an ordered validated array of `{code, message, details?}` records.

Migrate an existing non-empty `warning_code`/`warning_message` pair into a one-element warning array. The new array is authoritative. During compatibility migration, API payloads may continue exposing the first warning through the legacy scalar fields, but all first-party writers and UI must consume the full `warnings` collection. Warning helpers upsert or remove their own stable code without replacing other codes. Define `card_classification_mismatch` alongside the existing `matched_deprecated_card`, with deterministic presentation order when both apply.

The structured evidence should be sufficient to render messages such as:

- `Hero — detected tag "Hero"`
- `Location — detected tag "Location"`
- `Event — inferred from template "event-v1"`
- `Standard — no special role detected`
- `Needs review — inferred roles differ from the existing card`

Do not store provider-specific OCR internals in these classification fields.

## Core inference service

Add an import-owned core classifier, for example under `card_reader_core.services.imports`, with a small typed input and output:

- input: batch pool, role mode, override roles, snapshotted template roles, inference-policy version, and normalized matched tag keys;
- output: resolved role set plus structured evidence.

Automatic resolution is:

```text
resolved roles = template role hints union tag-derived roles union future code-owned inference
```

Policy version 1 contains `hero tag -> hero role`. Policy version 2 preserves that mapping and adds `location tag -> location role`. Keep each version's mapping centralized and independently testable so queued version 1 jobs remain Hero-only and are never reinterpreted by a later deployment.

Override mode bypasses all automatic signals and records that the result came from a batch override.

The classifier must be deterministic, order-independent, deduplicated, and return roles in the canonical code-owned order.

## Parser and persistence flow

Update `card_reader_core.services.parser_jobs.ImportProcessorService` rather than coupling the API to parser modules.

For each item:

1. Parse the image using the existing parser boundary.
2. Resolve stable matched tag keys from the parsed tag IDs and loaded metadata resources.
3. Call the core import classifier with the immutable job/item snapshot and its policy version.
4. Pass the resolved pool, roles, and evidence into the card persistence service.
5. In one transaction, persist the card/version result, resolved roles/evidence, every warning, and the item's terminal completed state.
6. Run post-success notifications or UI-facing refresh hooks as independent work that cannot rewrite the completed item as failed.

Persistence behavior:

- New card: assign the job pool and resolved roles in the same transaction as card identity creation.
- Existing card resolved inside the selected pool with equal roles: persist the new version normally.
- Existing card resolved inside the selected pool with a different role set: persist the valid parsed version, preserve the card's existing roles, and mark the item completed with `card_classification_mismatch`.
- Same name or image hash in another pool: after Step 2.1, create or resolve an independent card in the selected pool; do not emit a cross-pool classification mismatch.
- Targeted reparse: never changes card-level classification; compare the inference result with the live classification, preserve the live value, and warn on mismatch. The queued per-item target snapshot remains audit evidence if staff classification changes while the reparse waits.

If any card/version/audit/warning write fails, the transaction rolls back and item failure remains governed by the existing parser-job failure path. `ImportProcessorService` may transition an item to failed only when the authoritative persistence transaction did not commit; catching a later auxiliary error must not overwrite an already completed item. Do not mark failed persistence as a classification warning.

### Reparse job construction

Bulk template and maintenance reparses may target cards with different pools and role sets. They must not copy a fictional job-wide classification or look for originating-job lineage on `CardVersion`.

- Partition system-generated reparse jobs by selected template and canonical target classification so every job-wide pool remains truthful.
- Store each target card's pool and canonical roles on its `ImportJobItem` at queue time, even within a homogeneous partition.
- Use automatic inference with the snapshotted template hints and policy version to produce explainable evidence; the target snapshot is an audit baseline, not a role override.
- At processing time, preserve the card's live classification. If it changed after queuing, retain both the queued snapshot and current value in evidence and add a stable warning rather than restoring stale values.
- A retry copies the original job and per-item snapshots byte-for-byte. An explicit new reparse takes fresh snapshots.

## API contracts

Extend `POST /imports/upload` with typed form fields:

- `creation_key`;
- `card_pool`;
- `card_role_mode`;
- repeated or JSON-encoded `card_role_override` values, using one documented representation consistently.

Do not rely on the caller to place these values into `options_json`. The API serializer validates the combination and `ImportService.create_job` snapshots the template hints before creating the job.

The create response exposes `job_id` and `idempotent_replay`. Add an authenticated lookup such as `GET /imports/by-creation-key/{creation_key}` that returns the same job summary or a definitive `404`; it must not disclose jobs outside the endpoint's existing staff boundary.

Import list/detail payloads expose:

- batch pool;
- role mode;
- override roles when applicable;
- item resolved roles;
- structured inference evidence;
- the complete ordered warnings collection, with legacy scalar warning fields derived only for compatibility;
- target card/version identifiers and a usable Card-tab link when persistence succeeded.

Retry creation must copy the original job and item snapshots, including policy version and warning/audit inputs, unless the user explicitly starts a new import. Reparse creation follows the per-item target snapshot contract above. Neither path is an opportunity to reinterpret the original request.

## Frontend import workflow

Extend `frontend/src/features/import-jobs` without moving import-specific state into shared code.

In the Card setup section:

1. Require a visible pool selection. Step 2 implemented Player/Game Master; Step 2.1 changes the available values to Player/Evil/Neutral.
2. Default classification to **Automatic**.
3. Explain that automatic mode combines template hints and detected metadata.
4. Provide an **Override** mode with Hero, Boon, Event, and Location multi-select controls.
5. Present **Standard — no special roles** as the empty override state.
6. Include the stable creation key, pool, mode, override roles, template, content version, and files in the immutable submit payload.

Do not silently remember a prior batch override as the next batch's default. After a successful or reconciled submission, reset role mode to Automatic and rotate the creation key. While a submission or reconciliation is active, block in-app navigation and register browser-unload protection. After an ambiguous response, lock the exact attempt, reconcile by creation key, and offer retry only with the same payload; navigating away requires explicit confirmation, while editing the form explicitly abandons that attempt and generates a new key. The pool may default from the current workspace once Step 3 exists; before that, default visibly to Player.

Import activity/detail UI must show classification and warning evidence. A mismatch should provide a direct link to the resulting card's Card tab so staff can decide whether to edit the stored classification or correct the import setup.

In the template admin UI, add an inferred-role multi-select separate from the parsing-definition JSON editor. Template preview behavior remains unchanged.

Verify all new controls and warnings in light and dark themes.

## Implementation sequence

1. Add template, import-job, and import-item fields, multi-warning migration, creation-key uniqueness, and migrations.
2. Extend core template validation and APIs with inferred role hints.
3. Update template seeds and the Version 3 developer-data contract, adapters, coverage/doctor checks, and publication validation.
4. Implement and unit-test the versioned deterministic core inference service.
5. Add upload idempotency/reconciliation and snapshot template hints, policy version, and pool/mode/override during job creation.
6. Add per-item reparse snapshots and partition bulk reparses by target classification.
7. Integrate inference, audit evidence, multi-warning persistence, and terminal success into one parser-item transaction.
8. Add mismatch warning/audit payloads to import serialization.
9. Add template-admin inferred-role controls.
10. Add import pool, automatic/override, idempotent reconciliation, and result/warning UI.
11. Update current-state import/card/developer-data documentation after behavior ships.
12. Run all permitted validation before beginning [Step 2.1](card-classification-step-2-1-pool-scoped-identity.md).

## Required tests

Add or update tests covering:

- template role validation, normalization, and API round-trip;
- template seed and developer-data Version 1/2 adoption plus Version 3 round-trip;
- developer-data coverage/doctor failure when a required inference hint is missing;
- automatic mode as the default;
- upload creation replay, conflicting-key rejection, response-loss lookup, and no duplicate upload/job/content-version/items;
- Hero and Location inferred from their stable tag keys under policy version 2;
- Boon/Event/Location and multi-role inference from template hints;
- policy version 1 ignoring Location while preserving Hero inference;
- union and deterministic ordering across inference sources;
- no signals resolving to Standard/empty roles;
- override replacing, rather than augmenting, automatic inference;
- empty override forcing Standard;
- job snapshot stability after later template edits and inference-policy deployments;
- new-card classification assignment;
- existing-card exact match;
- same-pool role mismatch and targeted-reparse pool-snapshot mismatch preserving existing classification while completing with warning;
- deprecated-card and classification-mismatch warnings coexisting without overwrite;
- audit evidence, warnings, and terminal completion committing atomically with the parsed version;
- post-success auxiliary failure preserving completed state;
- targeted reparse preserving classification and retaining its per-item target snapshot;
- mixed-classification bulk reparses producing truthful partitions and per-item evidence;
- classification edits while a reparse is queued preserving the live value and warning with both snapshots;
- immutable retry payload, item snapshot, and inference-policy behavior;
- import form validation, reset behavior, request payload, and result/warning presentation;
- template-admin inferred-role editing.

Do not run prohibited service/integration suites. Run lint and typecheck for core, parser, API, and web, Django checks, and affected permitted frontend unit tests.

## Acceptance criteria

- Every new import job has an explicit pool and immutable classification snapshot.
- Ambiguous upload responses can be reconciled by creation key without duplicate jobs, content versions, items, or parser work.
- Automatic inference is the visible and API default.
- Hero and Location are inferred from their matched stable tag keys for new policy-version-2 jobs.
- Template hints can infer Boon, Event, Hero, Location, or any valid combination.
- Staff can override a batch with multiple roles or forced Standard.
- New cards receive the resolved pool and roles.
- Existing cards are never silently reclassified by import or reparse.
- Classification mismatches are durable, explainable, coexist with lifecycle warnings, and link to manual Card-tab correction.
- Parsed versions, audit evidence, warnings, and completed item state commit atomically; later auxiliary failures cannot turn confirmed success into failure.
- Later template edits or inference-policy releases do not change queued/retried job classification.
- Bulk reparses preserve truthful per-item target classification without relying on unavailable originating-job lineage.
- Template inference hints survive seeds, developer-data export/import, and clean-checkout bootstrap.
- No parser-specific type leaks into the API or core classification contract.
- Lint, typecheck, Django checks, affected permitted tests, and documentation validation pass.

## Explicit non-goals

- Per-file role overrides inside one batch.
- OCR inference from arbitrary unrecognized free text.
- Automatic pool inference.
- Automatically resolving classification mismatches.
- The global Player/Evil/Neutral workspace selector.
- Relaxing Evil/Neutral access beyond staff.
