# Imports and Parsing

Card imports turn one or more uploaded images into card records that can be reviewed, corrected, and used throughout the application. Processing is asynchronous so uploads do not keep an HTTP request open while OCR and image analysis run.

## End-to-end flow

1. A staff user uploads supported image files from the staff-only `/imports` interface, explicitly selecting the Player, Evil, or Neutral pool and either automatic role inference or a batch-wide role override.
2. The API admission boundary fingerprints the immutable request, stages and checksum-verifies each source file before atomically publishing it under the client-generated creation key, then asks core to create the content version, import job, and queued items in one transaction. Replaying the same key and payload returns the existing job; reusing the key for a different payload is rejected.
3. The parser worker polls for work and atomically claims a queued item.
4. The parser loads the selected parsing template and current catalog resources, then crops regions, runs OCR, extracts fields, and detects symbols.
5. Core resolves card roles from the job's snapshotted template hints and versioned metadata policy, then matches image hashes, primary names, and aliases inside the selected pool before persisting the card identity, card version, image, metadata relations, parsing suggestions, classification evidence, warnings, and processing result.
6. The import job reports aggregate progress while completed items become available in Review and the card detail editor.

Claiming is coordinated through the shared core layer. This prevents the API, parser, and any future background worker from inventing separate queue semantics.

## Service responsibilities

- The API owns HTTP upload streaming, request authorization, fingerprint-isolated staging, admission responses, cancellation requests, and retry actions. Its upload view delegates claimed/discarded/uncertain lifecycle decisions to the import admission boundary.
- The parser owns polling, OCR adapters, region parsing, symbol detection, and extraction logic. It does not depend on API views or serializers.
- Core owns creation prevalidation, the atomic content-version/job/item transaction, grouped reparse planning, job claiming, persistence, state transitions, storage paths, and the domain services used by both processes. Template and maintenance reparses use the same grouped operation and transaction.

The API and parser share the database and storage root. In the standard development and production layouts they run as separate processes, so both must be running for queued items to advance.

The staff-only `/operations` page groups monitoring around each durable queue. Select Card imports
to see its aggregate parser health, expand the pool to inspect individual worker instances, and page
through recent import jobs in newest-update order. `/imports` remains the place to create imports
and interrupt active work. Worker heartbeats distinguish an idle parser from a process that has
stopped reporting; they are operational telemetry and do not replace durable import job state.

## Templates and catalogs

Parsing templates describe where fields and symbols appear on a card image and how those regions should be interpreted. Catalogs provide the known keywords, tags, symbols, and card types used to match extracted text and detected artwork to application metadata.

Templates and catalogs are read at processing time. Changing them affects future parsing and explicit reparses; it does not silently rewrite existing card versions. Import classification is the exception to that live lookup: each job snapshots its template role hints and inference-policy version so queued or retried work keeps its original meaning.

Templates may declare any combination of Hero, Boon, Event, and Location role hints. Automatic classification unions those hints with stable metadata signals. Policy version 1 recognizes the `hero` tag key; policy version 2 preserves Hero inference and adds the `location` tag key. Override mode replaces every automatic signal with the selected role set; selecting no roles intentionally produces Standard. The pool is always explicit and is never inferred from a role.

## Jobs, retries, and cancellation

An import job is the user-facing batch, while import items are the individual units claimed by workers. Item state is durable, allowing the UI to show queued, processing, completed, failed, or cancelled work even if a process restarts.

Upload creation is idempotent. The browser retains one creation key and the exact submit payload until the server confirms the job, the browser reconciles it through the creation-key lookup, or the user explicitly abandons the attempt. In-app navigation is blocked while submission or reconciliation is active. An uncertain attempt is locked against edits, protected by route and browser-unload prompts, and can only be retried unchanged, preventing a lost HTTP response from creating duplicate content versions or parser work.

Staged uploads are unclaimed until the core transaction confirms durable ownership. Definitive validation or creation rejection removes only files owned by that exact fingerprint stage; confirmed success never cleans them up. If an unexpected infrastructure failure leaves ownership genuinely unknown, the isolated stage is preserved and logged for bounded reconciliation instead of risking deletion of committed work. Cleanup errors are reported separately and cannot replace a confirmed success, conflict, or validation response.

Cancellation stops work that has not yet completed. The centered `/imports` workspace groups card
setup, content-version details, and image or folder selection in one form. Images can be dropped
onto the source picker or selected with the native image and folder dialogs. A compact activity
area beside the form on wide screens, and below it on smaller screens, shows cancellable
active jobs and the five most recent finished jobs. Complete paged queue history remains available
under `/operations`; its latest page refreshes automatically while older pages remain stable during
inspection. Active jobs, recent history, and an open detail are refreshed through one activity
coordinator. Each read keeps independent error state, stale responses cannot replace newer manual
selection, and a non-terminal open detail receives its terminal refresh even after the active list
becomes empty. Failed or cancelled items can be retried through supported API and UI flows rather than
by manually editing database state. Worker claims and state transitions are designed to avoid two
workers completing the same queued item.

## Review and card history

Parser output is intentionally reviewable rather than treated as unquestionable source data. Reviewers can inspect images, parsed values, symbols, metadata matches, and suggestions before correcting the card version.

New cards receive the import pool and resolved roles. An untargeted import never attaches to a same-name, same-alias, or same-image card from another pool; it creates an independent identity without a role-mismatch warning. Existing same-pool cards and targeted reparses keep their stored card-level classification. When the inferred result differs after a same-pool or id-driven match, the parsed version still completes and the item records an explainable `card_classification_mismatch` warning alongside any lifecycle warning. Import details link directly to the Card tab for an intentional manual correction.

Import details show resolved roles and inference evidence only after the parser has persisted that evidence. Queued or active items are marked as classification pending, while terminal items that never produced evidence are marked unavailable rather than being presented as Standard.

Reparsing creates new content through the card-version workflow instead of erasing historical state. See [Card management](card-management.md) for the distinction between a stable card identity and its versions.
