# Card Classification Step 2.2: Import Workflow Seam Consolidation

Status: approved implementation plan; blocked on completion and merge of [Step 2.1](card-classification-step-2-1-pool-scoped-identity.md).

This is a hardening checkpoint between import inference/identity and the Player/Evil/Neutral workspaces:

1. [Card classification foundation](card-classification-step-1-foundation.md)
2. [Authorization seam consolidation](card-classification-step-1-1-authorization-seam.md)
3. [Import inference](card-classification-step-2-import-inference.md)
4. [Pool-scoped card identity](card-classification-step-2-1-pool-scoped-identity.md)
5. Import workflow seam consolidation (this document)
6. [Player, Evil, and Neutral workspaces](card-classification-step-3-card-pool-workspaces.md)

Do not add workspace behavior in this checkpoint. Step 2.2 consolidates the lifecycle and state-management contracts established by Step 2 so later work does not have to reproduce them across more entry points.

## Outcome

Replace branch-specific import and reparse safeguards with explicit, reusable workflow seams.

After this step:

- upload admission has one authoritative staged, claimed, or discarded lifecycle;
- idempotent replay, conflicting payloads, definitive validation failures, and ambiguous failures follow one outcome policy;
- grouped template and maintenance reparses use one transactional core operation;
- active jobs, recent history, and an open job detail refresh through one frontend activity boundary;
- pending, resolved, warning, and terminal item presentation derives from explicit state rather than empty JSON defaults;
- neutral import contracts do not create repository-to-service dependency cycles;
- architecture and state-matrix tests prevent the workflow from scattering again.

This checkpoint intentionally preserves Step 2's public behavior. Its success is measured by removing duplicated lifecycle decisions while keeping the hardened failure matrix green.

## Why this checkpoint exists

Step 2 review found a consistent pattern across otherwise separate comments:

- uploads needed atomic publication so interrupted requests could not expose partial files;
- different fingerprints under one creation key needed isolated staging directories;
- exact attempts needed navigation protection and creation-key reconciliation after ambiguous responses;
- definitive template validation failures needed to discard unclaimed files;
- grouped template and maintenance reparses independently needed all-or-nothing job creation;
- import-detail requests needed sequencing so stale responses could not replace the selected job;
- polling, manual refresh, and cancellation independently needed to refresh the open detail through terminal state;
- empty evidence on queued items needed an explicit pending presentation;
- structured inference and mismatch evidence needed a shared renderer;
- inference types needed a neutral owner so repositories did not import a higher service layer.

Each fix is valid, but the repeated shape shows that the workflow lacks one place where authoritative success, idempotency, independent failure domains, and cleanup semantics are declared and enforced. Adding the Step 3 workspace on top of that distribution would increase the number of callers and refresh triggers before the seam is stable.

## Locked decisions

- Preserve every Step 2 API field, status, warning, inference, and idempotency contract unless a change is explicitly documented here.
- `ImportJob` plus all initial `ImportJobItem` rows remain the authoritative success condition for import creation.
- The API owns HTTP upload streaming and filesystem staging. Core remains independent of Django REST Framework and `UploadedFile`.
- Core owns template/content-version validation, immutable job snapshots, transactional job/item creation, grouped reparse planning, and persistence outcomes.
- A staged upload is unclaimed until durable job creation confirms that exact source directory belongs to the job.
- Definitive rejection discards unclaimed staged files. Confirmed success never does.
- An uncertain infrastructure failure must reconcile by creation key before cleanup. If durable ownership cannot be determined safely, preserve the isolated stage for bounded orphan reconciliation rather than risking deletion of claimed work.
- Matching idempotent replay returns the existing job before creating another stage. A conflicting fingerprint never shares files with the winning job.
- Cleanup is an independent failure domain. Cleanup failure is logged and made observable, but it does not replace an authoritative success or a definitive domain response.
- Grouped reparse creation is one core operation and one database transaction. Template and maintenance endpoints supply policy inputs and presentation copy only.
- Import activity remains feature-owned under `frontend/src/features/import-jobs`; do not create an app-global import store.
- Active list, recent history, and selected detail may fail independently, but every refresh trigger uses one coordinator that applies consistent request sequencing.
- Background refresh must never supersede a newer user-selected detail request.
- A non-terminal open detail receives one final terminal refresh after completion, failure, or cancellation. Terminal details are not polled indefinitely.
- Do not add a queue broker, distributed lock, new import schema, or generic workflow framework in this checkpoint unless implementation proves one is unavoidable.

## Delivery and dependency order

- Finish and merge the Step 2.1 checkpoint PR into `feature/card-classification` first.
- Create `feature/card-classification-step-2-2-import-workflow-seam` from the updated umbrella branch.
- Open the Step 2.2 PR against `feature/card-classification`, not `master`.
- Keep the aggregate feature PR to `master` open so the combined classification work continues receiving CI and review.
- Merge Step 2.2 into the umbrella only after its acceptance criteria and review are clear.
- Create the Step 3 branch from the newly updated umbrella branch so the workspace diff does not contain Step 2.2 implementation commits.

## Authoritative success and failure domains

### Upload admission

Define one API-owned upload-admission component, for example under `card_reader_api.imports.creation`, that owns:

1. normalized request fingerprinting;
2. early domain prevalidation that can happen before file persistence;
3. fingerprint-isolated staging and atomic file publication;
4. invocation of the core job-creation operation;
5. conversion of the result into claimed, replayed, conflicted, rejected, or uncertain outcomes;
6. cleanup or preservation according to that outcome.

Represent a staged upload with an explicit object or context-managed value containing at least the creation key, fingerprint, storage-relative path, and claimed state. The object may delete only its own validated fingerprint directory. It must not recursively target an unresolved environment path, creation-key parent shared by another fingerprint, storage root, or another job's directory.

The outcome matrix is:

| Outcome | Durable job | Staged files | Response behavior |
| --- | --- | --- | --- |
| First success | Created once | Claimed | `201` |
| Matching replay | Existing | No new stage | Existing payload with `idempotent_replay=true` |
| Conflicting fingerprint | Existing winner | Losing stage discarded | `409` |
| Definitive domain rejection | None | Discarded | Existing `400` contract |
| Interrupted file stream | None | Partial staging file removed | Request fails; same exact attempt can retry |
| Ambiguous client response | Created or still processing | Claimed/preserved | Client reconciles by creation key |
| Unexpected server failure before ownership is known | Unknown until lookup | Preserve unless a definitive miss is established | Existing generic failure, logged for reconciliation |

Prevalidate template existence and other side-effect-free domain inputs before staging when possible. The staged-upload lifecycle remains required because validation and transactional failures can still occur after bytes arrive.

Do not catch every exception and infer that no commit happened. Reconciliation or a typed core outcome must establish whether the job owns the stage.

### Core creation operation

Keep or evolve the existing import service rather than adding a parallel creator. Its public create operation must:

- accept normalized domain inputs and an already published storage-relative source directory;
- validate template and content-version rules through owned core helpers;
- snapshot pool, role mode, override roles, template hints, and inference-policy version;
- create the content version, job, and every initial item inside one transaction;
- distinguish matching replay, fingerprint conflict, definitive validation rejection, and created success through typed exceptions or a typed result;
- never inspect HTTP requests, browser state, or `UploadedFile` objects.

Place shared evidence and creation result types in a neutral import-owned types module that repositories and services may both depend on. Repositories must not import a service package merely for annotations.

### Grouped reparses

Add one core grouped-reparse operation consumed by template and maintenance workflows.

The operation receives normalized reparse sources plus explicit target template/options and:

1. partitions sources by selected template, pool, and canonical role set;
2. builds item target snapshots for every source;
3. creates every required job inside one outer transaction;
4. returns a typed summary containing job and item counts.

Endpoint or maintenance callers retain their authorization, query/filter selection, HTTP status, and user-facing message ownership. They must not duplicate the grouping loop or add their own transaction around repeated low-level job creation.

Source images already exist for reparses, so database rollback is authoritative. No reparse cleanup may delete card images.

## Frontend import activity seam

Extract the activity portion of `useImportJobsController` only as far as needed to give refresh behavior one owner. A feature-local composable such as `useImportActivity` may own:

- active jobs and their request generation;
- recent operations history and pagination;
- the selected detail and its latest-request identity;
- polling pause/resume state;
- refresh timestamps and independent list/history/detail errors;
- reconciliation when history reveals work missing from the active snapshot.

Expose one refresh operation used by:

- initial mount;
- the manual Refresh action;
- polling;
- successful creation;
- successful cancellation;
- visibility restoration.

The coordinator may refresh list, history, and detail concurrently when safe. It must preserve these rules:

- stale list, history, or detail responses cannot replace newer state;
- a background detail refresh cannot supersede a manual selection request;
- failure in one read does not erase successful state from another read;
- if the selected detail was non-terminal at refresh start, refresh it even when the active list becomes empty;
- once the refreshed detail becomes terminal, stop background detail polling;
- closing or replacing the selected detail prevents an older response from reopening it;
- cancellation success is authoritative even when a follow-up read fails, and the UI reports the refresh problem separately.

Keep the create-attempt state machine separate from activity reads. It continues to own immutable files/form values, before-unload and route-leave protection, reconciliation, retry, explicit abandonment, and creation-key rotation.

## Evidence and status contracts

Centralize feature-local presentation helpers for import item evidence:

- queued or running with no persisted inference evidence: `pending`;
- completed with evidence: `resolved`;
- completed with warning evidence: `resolved_with_warning`;
- failed before evidence: `unavailable`;
- terminal with persisted evidence: render that evidence even if the item also has warnings.

Render canonical role labels and structured template/tag/override evidence through the shared card-role registry established in Step 2. Do not treat empty `resolved_card_roles` as Standard until persistence state proves classification ran.

Warnings remain ordered domain records. UI helpers may format known details but must retain a safe generic fallback for future warning codes and fields.

## Implementation sequence

1. Capture the current Step 2 behavior in an executable creation/reparse/activity state matrix.
2. Move shared import evidence and creation result contracts to a neutral import-owned types module; remove repository-to-service annotation dependencies.
3. Extract API upload admission into one owned component with explicit staged/claimed/discarded semantics.
4. Move side-effect-free template and content-version prevalidation before staging where possible.
5. Refactor upload creation to consume typed core outcomes and apply the centralized cleanup/reconciliation matrix.
6. Add bounded orphan-stage observability or reconciliation for genuinely uncertain server failures; do not add an unbounded destructive cleanup sweep.
7. Consolidate template and maintenance grouped reparses behind one transactional core operation.
8. Consolidate frontend active/history/detail refresh behavior in one feature-local activity seam.
9. Centralize pending/resolved/evidence presentation and use the shared role formatter.
10. Remove obsolete branch-specific cleanup, grouping, refresh, and evidence logic after all callers use the seam.
11. Add architecture guards for the new ownership boundaries.
12. Update current-state import/operations documentation if module ownership or operational recovery changes.
13. Run all permitted validation and complete a final state-matrix audit before starting Step 3.

## Required tests

### Upload creation

- first creation produces one content version, job, item set, and claimed fingerprint directory;
- matching replay produces no new filesystem or database state;
- a conflicting fingerprint cannot enter or delete the winner's directory;
- interrupted streaming leaves no published or temporary file and can retry with the same key;
- unknown/stale template and other definitive validation failures remove unclaimed files;
- content-version/job/item transaction failure rolls back all durable rows and discards a definitively unclaimed stage;
- ambiguous response reconciliation finds committed success without duplication;
- an ownership lookup failure preserves the isolated stage and logs the uncertain outcome;
- cleanup failure does not replace confirmed success or the intended domain response;
- cleanup path validation cannot escape the exact staged fingerprint directory.

### Grouped reparses

- mixed pools and role sets partition deterministically;
- template and maintenance callers produce the same partition contract;
- failure creating a later group rolls back every earlier job and item;
- successful summary counts match committed jobs/items;
- per-item classification snapshots remain intact;
- rollback never deletes existing source card images.

### Frontend activity

- older active, history, and detail responses cannot replace newer state;
- polling refreshes an open running detail through its terminal result;
- cancelling the final active job refreshes its open detail after polling stops;
- manual refresh updates an open non-terminal detail;
- a manual detail selection wins over an overlapping background refresh;
- closing a detail while refresh is in flight does not reopen it;
- list, history, and detail failures remain independent and preserve successful sibling state;
- terminal details stop background refresh;
- pending, Standard, multi-role, warning, and unavailable evidence states render correctly.

### Architecture guards

Add narrow source-boundary checks that fail when:

- API upload views directly implement staging cleanup branches instead of calling the admission seam;
- template or maintenance callers implement their own classification-group job loop;
- repositories import the public import service package for shared contracts;
- a new activity trigger refreshes only lists while bypassing selected-detail reconciliation.

## Validation

Do not run prohibited service/integration suites locally. Run:

```text
pnpm --filter @card-reader/core lint
pnpm --filter @card-reader/core typecheck
pnpm --filter @card-reader/api lint
pnpm --filter @card-reader/api typecheck
pnpm --filter @card-reader/web lint
pnpm --filter @card-reader/web typecheck
pnpm --filter @card-reader/web test -- <affected import specs>
uv run --project ../.. --package card-reader-api python manage.py check
```

Add backend failure-matrix and architecture tests for CI. Manually verify the import form, activity panel, pending evidence, completed evidence, warnings, refresh, and cancellation in light and dark themes when visible UI code changes.

## Acceptance criteria

- Upload admission has one explicit staged, claimed, discarded, or uncertain lifecycle.
- Definitive rejection cannot leak uploaded files, and cleanup cannot delete a claimed or competing fingerprint directory.
- Matching replay and ambiguous-response reconciliation remain duplicate-free.
- Core job creation atomically owns the content version, job, items, and immutable classification snapshot.
- Template and maintenance reparses share one transactional grouping operation.
- Active jobs, recent history, and selected detail refresh through one feature-local coordinator.
- Polling, manual refresh, creation, cancellation, and visibility restoration preserve terminal detail consistency.
- Background responses cannot replace a newer manual selection or reopen a closed detail.
- Pending, resolved, Standard, warning, and unavailable evidence states are explicit and accurate.
- Shared import contracts live in a neutral owner and repository/service dependency direction remains valid.
- Architecture guards prevent cleanup, grouping, dependency, and refresh logic from scattering again.
- Step 2 public contracts and user-visible behavior remain compatible.
- Lint, typecheck, Django checks, affected permitted tests, CI tests, and documentation validation pass.

## Explicit non-goals

- New card roles, inference policies, pool rules, or per-file overrides.
- Player/Evil/Neutral sidenav or workspace scoping.
- Changing staff-only Evil/Neutral access.
- Parser/OCR algorithm changes.
- A generic workflow engine, external queue, or distributed lock service.
- Automatic cleanup of unrelated historical storage directories.
- Import-job cancellation semantics beyond keeping existing state and refresh behavior consistent.
- New deck, Evil/Neutral deck, Scenario, or Playtester behavior.
