# Imports and Parsing

Card imports turn one or more uploaded images into card records that can be reviewed, corrected, and used throughout the application. Processing is asynchronous so uploads do not keep an HTTP request open while OCR and image analysis run.

## End-to-end flow

1. A staff user uploads supported image files from the staff-only `/imports` interface, explicitly selecting a parsing template and the Player, Evil, or Neutral pool, then choosing Automatic or an exact batch-wide Override independently for roles, factions, and mana families. Template and pool start unselected for every new import and never inherit the active site workspace, so each queued batch records an intentional choice.
2. The API admission boundary fingerprints the immutable request, stages and checksum-verifies each source file before atomically publishing it under the client-generated creation key, then asks core to create the content version, import job, and queued items in one transaction. Replaying the same key and payload returns the existing job; reusing the key for a different payload is rejected.
3. The parser worker polls for work and atomically claims a queued item.
4. The parser loads the selected parsing template and current catalog resources, then crops regions, runs OCR, extracts fields, and detects symbols.
5. Core resolves roles, factions, and mana families from the job's immutable snapshot of enabled, pool-specific Tag, Type, and Symbol rules, then matches image hashes, primary names, and aliases inside the selected pool and exact faction namespace. When an untargeted Evil import resolves no faction, Core treats that result as unknown and may recover one uniquely identified factioned Evil Card from historical image checksums or its normalized primary name or aliases before persisting the card identity, card version, image, metadata relations, parsing suggestions, classification evidence, warnings, and processing result.
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

Templates configure parsing only; they do not classify cards. Staff manage explicit inference rules under **Admin → Catalog → Card classification**. Each enabled rule maps one existing Tag, Type, or Symbol to one code-owned role, faction, or mana family in exactly one pool. Automatic classification unions every matching rule from the job snapshot, while the three overrides independently bypass rules for their facet. Selecting no roles produces Normal and no mana families produces Colorless. An empty faction result produces No faction in Player and Neutral; in Evil it means unknown and starts the bounded matching and review behavior described below. The pool is always explicit and is never inferred. Default Player and Evil rules map the Mana Type to the Mana role without assigning a mana family or faction. Evil-only defaults likewise map the Directive and Reminder Types to their matching roles; Player and Neutral can use those roles only through manual assignments or custom rules. Default Player rules separately map every available paired mana and affinity Symbol to its family; missing Symbols are never synthesized. New jobs snapshot these defaults. During the one-time migration from the pre-classification schema, still-active Player jobs receive only the available mana-family Symbol rules plus targeted mana-family evidence; completed jobs and the adopted jobs' role/faction meaning remain unchanged. After that adoption, every job snapshot is immutable.

Template regions use one of these parser types: `name`, `name_mana_cost`, `type_tag`, `rules_text`, `attack`, `health`, or `affinity`. Use `name` when a crop contains only the card name; it performs OCR and shared name cleanup without loading mana symbols or running symbol detection. Use `name_mana_cost` when the crop contains both the name and mana cost. Its cost policy follows the import pool: Player retains symbol-derived costs and `X` handling, Evil validates OCR-derived costs against the mana badge without running top-bar symbol detection, and Neutral leaves the cost fields empty. A `name_mana_cost` region may configure `mana_badge_ocr` with a `cut_region` relative to that name region and optional integer `scales` from 1 through 4. For every Evil parse with that configuration, the parser OCRs the isolated badge and accepts a standalone integer or `X` from it as the authoritative cost. A trailing integer from the full name-region OCR is treated as mana, and removed from the parsed name, only when the isolated badge reports the same numeric value or the primary OCR exposes that exact integer as a standalone line inside the configured badge bounds. If the isolated badge reports a different value, that badge value remains authoritative and the trailing title digits are preserved; if neither validation succeeds, the digits remain part of the name and the cost fields stay empty. The isolated evidence and validation decision are merged into the region diagnostics. Existing and immutable bundled `mtg-like-v1` definitions are upgraded with the compatible badge configuration during migration or developer-data import. Without that configuration, Evil cost fields remain empty. These pool-specific choices affect only the name-and-cost region; affinity and rules-region symbol detection continue independently. A template may have at most one name-producing region across those two types. Templates without either remain valid and use the source image stem as the final name fallback.

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

New cards receive the import pool plus resolved roles, factions, and mana families. Untargeted imports normally match only inside the selected pool and exact faction namespace; mana families do not affect matching. For an Evil import with no resolved faction and reparse matching enabled, Core first keeps ordinary empty-namespace matching, then considers currently factioned Evil Cards across every historical version with the same image checksum and every normalized primary name or alias matching the parsed name. A single checksum or name candidate may resolve the Card; when both are present they must identify the same Card. Multiple candidates from either source or conflicting singleton candidates refuse the merge. Existing cards resolved in the namespace and targeted reparses keep their stored card-level classification. When inferred values differ from the stored Card, the parsed version still completes, preserves the Card classification, and creates a durable staff Classification review item containing both snapshots and the inference evidence. The import displays a neutral Review handoff rather than a warning. Reviewers edit the Card if needed and explicitly resolve the item or keep the existing classification. An unmatched or ambiguous Evil import completes on a transitional no-faction Card with `evil_faction_unresolved`, candidate counts, and a Card-tab review link. Targeted reparses, known-faction imports, Player and Neutral, and imports with reparse matching disabled retain their existing behavior.

Import activity shows the job snapshot's rule count and digest. Item details show resolved roles, factions, and mana families plus matching Tag, Type, and Symbol sources after the parser has persisted that evidence. Queued or active items are marked as classification pending, while terminal items that never produced evidence are marked unavailable rather than being presented as an empty derived state. Automatic classification with no matching rules is a completed Normal/No faction/Colorless result, except that an empty Evil faction result is explicitly flagged for review rather than presented as reviewed stable classification. Mismatch evidence includes stored/live values, the queued snapshot when applicable, inferred values, and matching rules, with a direct Card-tab review link.

Reparsing creates new content through the card-version workflow instead of erasing historical state. See [Card management](card-management.md) for the distinction between a stable card identity and its versions.
