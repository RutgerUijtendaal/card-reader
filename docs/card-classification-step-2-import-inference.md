# Card Classification Step 2: Import Inference

Status: approved implementation plan; blocked on [Step 1](card-classification-step-1-foundation.md).

This step adds reliable, explainable import classification on top of the pool and role model. It must not reintroduce Hero-specific persistence or allow an import to silently reclassify an existing card.

## Outcome

Every import batch selects exactly one card pool and defaults to automatic role inference. Automatic inference unions roles declared by the selected template with roles inferred from parsed metadata. Staff can instead choose an explicit batch-wide role override, including forced Standard.

New cards receive the batch pool and resolved roles. Existing cards are updated only when their stored classification agrees; a mismatch completes with a durable warning and preserves the existing card classification for manual review in the Card tab.

## Locked decisions

- Card pool is always an explicit batch choice. It is not inferred from roles or template.
- Role mode is either `automatic` or `override`; automatic is the default.
- Overrides are complete batch-wide role sets, not additions to inferred roles.
- An empty override means intentionally force Standard.
- Automatic inference unions all matching signals and therefore supports multiple roles.
- The stable tag key `hero` infers the Hero role. Do not infer from localized labels or free text when a matched tag key is available.
- Templates declare zero or more inferred role hints. The inference engine is generic and must not hard-code individual template IDs.
- No inferred role means Standard; Standard is never stored as a role.
- Existing card classification is authoritative. Import mismatches warn and preserve it; imports never silently move an existing card between pools or replace its roles.
- Manual Card-tab edits remain authoritative after import.
- Inference is core-owned and consumes normalized evidence. Parser code extracts evidence but does not own classification policy.

## Authoritative success and failure domains

Creating the `ImportJob` with its immutable pool, role mode, and override payload is the authoritative success condition for the upload mutation. Browser cleanup or navigation failures must not undo a confirmed job creation.

The upload, durable job creation, parser execution, classification resolution, card persistence, and post-processing UI refresh are independent failure domains. A completed parser item with a classification mismatch remains completed-with-warning; the warning must not roll back an otherwise valid parsed version.

Retries and reparses reuse the classification snapshot stored on the job. Later template edits must not change the meaning of an already queued or retryable import.

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
- add coverage or doctor validation for every template that is expected to infer a role, so a missing Boon/Event hint cannot silently turn imported cards into Standard after bootstrap.

### Import job

Add required fields to `ImportJob`:

- `card_pool`;
- `card_role_mode`, with `automatic` and `override` values;
- `card_role_override_json`, a normalized role array used only in override mode;
- `template_role_snapshot_json`, capturing the selected template's role hints at job creation.

Validation rules:

- automatic mode requires an empty override array;
- override mode accepts zero or more roles; zero means forced Standard;
- every role must be code-owned;
- the pool is always explicit and valid.

The template snapshot makes queued work deterministic even if staff edit the template before the parser processes the job.

### Import item

Add audit fields to `ImportJobItem`:

- `resolved_card_roles_json` for the automatic or overridden result;
- `card_role_inference_json` for structured evidence such as template hints and matched tag keys.

Continue using the existing `warning_code` and `warning_message` fields for mismatch presentation. Define a stable warning code such as `card_classification_mismatch`.

The structured evidence should be sufficient to render messages such as:

- `Hero — detected tag "Hero"`
- `Event — inferred from template "event-v1"`
- `Standard — no special role detected`
- `Needs review — inferred roles differ from the existing card`

Do not store provider-specific OCR internals in these classification fields.

## Core inference service

Add an import-owned core classifier, for example under `card_reader_core.services.imports`, with a small typed input and output:

- input: batch pool, role mode, override roles, snapshotted template roles, and normalized matched tag keys;
- output: resolved role set plus structured evidence.

Automatic resolution is:

```text
resolved roles = template role hints union tag-derived roles union future code-owned inference
```

Initial tag inference contains `hero tag -> hero role`. Keep the mapping centralized and independently testable. Future Boon/Event tag rules can be added without changing the parser adapter.

Override mode bypasses all automatic signals and records that the result came from a batch override.

The classifier must be deterministic, order-independent, deduplicated, and return roles in the canonical code-owned order.

## Parser and persistence flow

Update `card_reader_core.services.parser_jobs.ImportProcessorService` rather than coupling the API to parser modules.

For each item:

1. Parse the image using the existing parser boundary.
2. Resolve stable matched tag keys from the parsed tag IDs and loaded metadata resources.
3. Call the core import classifier with the immutable job snapshot.
4. Pass the resolved pool, roles, and evidence into the card persistence service.
5. Persist the parse/version result using existing transactional behavior.
6. Store the resolved roles/evidence on the item.

Persistence behavior:

- New card: assign the job pool and resolved roles in the same transaction as card identity creation.
- Existing card with equal pool and roles: persist the new version normally.
- Existing card with a different pool or role set: persist the valid parsed version, preserve the card's existing pool/roles, and mark the item completed with `card_classification_mismatch`.
- Targeted reparse: never changes card-level classification; compare the inference result and warn on mismatch.

If card/version persistence fails, item failure remains governed by the existing parser-job failure path. Do not mark a failed persistence as a classification warning.

## API contracts

Extend `POST /imports/upload` with typed form fields:

- `card_pool`;
- `card_role_mode`;
- repeated or JSON-encoded `card_role_override` values, using one documented representation consistently.

Do not rely on the caller to place these values into `options_json`. The API serializer validates the combination and `ImportService.create_job` snapshots the template hints before creating the job.

Import list/detail payloads expose:

- batch pool;
- role mode;
- override roles when applicable;
- item resolved roles;
- structured inference evidence;
- mismatch warning code/message;
- target card/version identifiers and a usable Card-tab link when persistence succeeded.

Retry/reparse job creation must copy the original classification snapshot and mode unless the user explicitly starts a new import. A retry is not an opportunity to reinterpret the original request.

## Frontend import workflow

Extend `frontend/src/features/import-jobs` without moving import-specific state into shared code.

In the Card setup section:

1. Require a visible Player/Game Master pool selection.
2. Default classification to **Automatic**.
3. Explain that automatic mode combines template hints and detected metadata.
4. Provide an **Override** mode with Hero, Boon, and Event multi-select controls.
5. Present **Standard — no special roles** as the empty override state.
6. Include pool, mode, override roles, template, content version, and files in the immutable submit payload.

Do not silently remember a prior batch override as the next batch's default. After a successful submission, reset role mode to Automatic. The pool may default from the current workspace once Step 3 exists; before that, default visibly to Player.

Import activity/detail UI must show classification and warning evidence. A mismatch should provide a direct link to the resulting card's Card tab so staff can decide whether to edit the stored classification or correct the import setup.

In the template admin UI, add an inferred-role multi-select separate from the parsing-definition JSON editor. Template preview behavior remains unchanged.

Verify all new controls and warnings in light and dark themes.

## Implementation sequence

1. Add template, import-job, and import-item fields plus migrations.
2. Extend core template validation and APIs with inferred role hints.
3. Update template seeds and the Version 3 developer-data contract, adapters, coverage/doctor checks, and publication validation.
4. Implement and unit-test the deterministic core inference service.
5. Snapshot template hints and validate pool/mode/override during job creation.
6. Integrate inference into parser-job orchestration and card persistence.
7. Add mismatch warning/audit payloads to import serialization.
8. Add template-admin inferred-role controls.
9. Add import pool, automatic/override, and result/warning UI.
10. Update current-state import/card/developer-data documentation after behavior ships.
11. Run all permitted validation before beginning Step 3.

## Required tests

Add or update tests covering:

- template role validation, normalization, and API round-trip;
- template seed and developer-data Version 1/2 adoption plus Version 3 round-trip;
- developer-data coverage/doctor failure when a required inference hint is missing;
- automatic mode as the default;
- Hero inferred from the stable Hero tag key;
- Boon/Event and multi-role inference from template hints;
- union and deterministic ordering across inference sources;
- no signals resolving to Standard/empty roles;
- override replacing, rather than augmenting, automatic inference;
- empty override forcing Standard;
- job snapshot stability after later template edits;
- new-card classification assignment;
- existing-card exact match;
- pool mismatch and role mismatch preserving existing classification while completing with warning;
- targeted reparse preserving classification;
- immutable retry payload behavior;
- import form validation, reset behavior, request payload, and result/warning presentation;
- template-admin inferred-role editing.

Do not run prohibited service/integration suites. Run lint and typecheck for core, parser, API, and web, Django checks, and affected permitted frontend unit tests.

## Acceptance criteria

- Every new import job has an explicit pool and immutable classification snapshot.
- Automatic inference is the visible and API default.
- Hero is inferred from the matched Hero tag key.
- Template hints can infer Boon, Event, Hero, or any valid combination.
- Staff can override a batch with multiple roles or forced Standard.
- New cards receive the resolved pool and roles.
- Existing cards are never silently reclassified by import or reparse.
- Classification mismatches are durable, explainable, and linked to manual Card-tab correction.
- Later template edits do not change queued/retried job classification.
- Template inference hints survive seeds, developer-data export/import, and clean-checkout bootstrap.
- No parser-specific type leaks into the API or core classification contract.
- Lint, typecheck, Django checks, affected permitted tests, and documentation validation pass.

## Explicit non-goals

- Per-file role overrides inside one batch.
- OCR inference from arbitrary unrecognized free text.
- Automatic pool inference.
- Automatically resolving classification mismatches.
- The global Player/Game Master workspace toggle.
- Relaxing Game Master access beyond staff.
