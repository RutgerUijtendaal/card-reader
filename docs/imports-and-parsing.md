# Imports and Parsing

Card imports turn one or more uploaded images into card records that can be reviewed, corrected, and used throughout the application. Processing is asynchronous so uploads do not keep an HTTP request open while OCR and image analysis run.

## End-to-end flow

1. A staff user uploads supported image files from the staff-only `/imports` interface, explicitly selecting a parsing template and the Player, Evil, or Neutral pool, then choosing Automatic or an exact batch-wide Override independently for roles and factions. Template and pool start unselected for every new import and never inherit the active site workspace, so each queued batch records an intentional choice.
2. The API admission boundary fingerprints the immutable request, stages and checksum-verifies each source file before atomically publishing it under the client-generated creation key, then asks core to create the content version, import job, and queued items in one transaction. Replaying the same key and payload returns the existing job; reusing the key for a different payload is rejected.
3. The parser worker polls for work and atomically claims a queued item.
4. The parser loads the selected parsing template and current catalog resources, then crops regions, runs OCR, extracts fields, and detects symbols.
5. Core resolves roles and factions from the job's immutable snapshot of enabled, pool-specific Tag and Type rules, then matches image hashes, primary names, and aliases inside the selected pool and exact faction namespace. A unique prior manual faction correction may also be recovered when a completed job in that pool produced a version with the same image and inferred factions before Core persists the card identity, card version, image, metadata relations, parsing suggestions, classification evidence, warnings, and processing result.
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

Templates and catalogs are read at processing time. Changing them affects future parsing and explicit reparses; it does not silently rewrite existing card versions. Classification rules are snapshotted when the job is created, so later rule edits, metadata renames, retries, or parser restarts cannot change that job's meaning. Snapshot validation requires the snapshot and every contained rule to match the job's explicit pool.

Templates configure parsing only; they do not classify cards. Staff manage explicit inference rules under **Admin → Catalog → Card classification**. Each enabled rule maps one existing Tag or Type to one code-owned role or faction in exactly one pool. Automatic classification unions every matching rule from the job snapshot, while role and faction overrides independently bypass all rules for their facet. Selecting no roles intentionally produces Normal; selecting no factions intentionally produces No faction. The pool is always explicit and is never inferred.

Template regions use one of these parser types: `name`, `name_mana_cost`, `type_tag`, `rules_text`, `attack`, `health`, or `affinity`. Use `name` when a crop contains only the card name; it performs OCR and shared name cleanup without loading mana symbols or running symbol detection. Use `name_mana_cost` when the crop contains both the name and mana cost. Its cost policy follows the import pool: Player retains symbol-derived costs and `X` handling, Evil reads the final OCR decimal integer without running top-bar symbol detection, and Neutral leaves the cost fields empty. An Evil crop without a valid trailing integer also leaves its cost fields empty. These pool-specific choices affect only the name-and-cost region; affinity and rules-region symbol detection continue independently. A template may have at most one name-producing region across those two types. Templates without either remain valid and use the source image stem as the final name fallback.

## Jobs, retries, and cancellation

An import job is the user-facing batch, while import items are the individual units claimed by workers. Item state is durable, allowing the UI to show queued, processing, completed, failed, or cancelled work even if a process restarts.

Upload creation is idempotent. The browser retains one creation key and the exact submit payload until the server confirms the job, the browser reconciles it through the creation-key lookup, or the user explicitly abandons the attempt. In-app navigation is blocked while submission or reconciliation is active. An uncertain attempt is locked against edits, protected by route and browser-unload prompts, and can only be retried unchanged, preventing a lost HTTP response from creating duplicate content versions or parser work.

Staged uploads are unclaimed until the core transaction confirms durable ownership. Definitive validation or creation rejection removes only checksum-matching files from that exact fingerprint stage; an exact retry also removes a preserved stage after confirming that rejection and the absence of a durable job. Confirmed success never cleans its source files. If an unexpected infrastructure failure leaves ownership genuinely unknown, the isolated stage is preserved and logged instead of risking deletion of committed work; abandoned uncertain stages currently require operator cleanup. Cleanup errors are reported separately and cannot replace a confirmed success, conflict, or validation response.

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

New cards receive the import pool plus resolved roles and factions. Untargeted imports normally match only inside the selected pool and exact faction namespace. One narrow correction path also reuses an image from another faction namespace when a prior completed job in the requested pool produced a version with that image and recorded the current inferred faction set, the Card still belongs to that pool but was subsequently reclassified, and exactly one Card has that provenance. This allows a repeated import to retain an intentional manual faction correction without conflating ambiguous same-art Cards, including when the provenance version is no longer latest. Existing matched Cards and targeted reparses keep their stored card-level classification. When roles or factions differ after a match, or any queued/live/inferred classification differs for a targeted reparse, the parsed version still completes and the item records an explainable `card_classification_mismatch` warning alongside any lifecycle warning. Import details link directly to the Card tab for an intentional manual correction.

Import activity shows the job snapshot's rule count and digest. Item details show resolved roles and factions, matched Tag and Type sources, and their separate evidence sections only after the parser has persisted that evidence. Queued or active items are marked as classification pending, while terminal items that never produced evidence are marked unavailable rather than being presented as Normal or No faction. Automatic classification with no matching rules is a completed Normal/No faction result, not unavailable.

Reparsing creates new content through the card-version workflow instead of erasing historical state. See [Card management](card-management.md) for the distinction between a stable card identity and its versions.
