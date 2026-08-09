# Imports and Parsing

Card imports turn one or more uploaded images into card records that can be reviewed, corrected, and used throughout the application. Processing is asynchronous so uploads do not keep an HTTP request open while OCR and image analysis run.

## End-to-end flow

1. A staff user uploads supported image files from the staff-only `/imports` interface.
2. The API stores the source files and creates an import job with one queued item per image.
3. The parser worker polls for work and atomically claims a queued item.
4. The parser loads the selected parsing template and current catalog resources, then crops regions, runs OCR, extracts fields, and detects symbols.
5. Core services persist the card identity, card version, image, metadata relations, parsing suggestions, and processing result.
6. The import job reports aggregate progress while completed items become available in Review and the card detail editor.

Claiming is coordinated through the shared core layer. This prevents the API, parser, and any future background worker from inventing separate queue semantics.

## Service responsibilities

- The API owns upload validation, request authorization, job creation, status responses, cancellation requests, and retry actions.
- The parser owns polling, OCR adapters, region parsing, symbol detection, and extraction logic. It does not depend on API views or serializers.
- Core owns job claiming, persistence, state transitions, storage paths, and the domain services used by both processes.

The API and parser share the database and storage root. In the standard development and production layouts they run as separate processes, so both must be running for queued items to advance.

The staff-only `/operations` page groups monitoring around each durable queue. Select Card imports
to see its aggregate parser health, expand the pool to inspect individual worker instances, and page
through recent import jobs in newest-update order. `/imports` remains the place to create imports
and interrupt active work. Worker heartbeats distinguish an idle parser from a process that has
stopped reporting; they are operational telemetry and do not replace durable import job state.

## Templates and catalogs

Parsing templates describe where fields and symbols appear on a card image and how those regions should be interpreted. Catalogs provide the known keywords, tags, symbols, and card types used to match extracted text and detected artwork to application metadata.

Templates and catalogs are read at processing time. Changing them affects future parsing and explicit reparses; it does not silently rewrite existing card versions.

## Jobs, retries, and cancellation

An import job is the user-facing batch, while import items are the individual units claimed by workers. Item state is durable, allowing the UI to show queued, processing, completed, failed, or cancelled work even if a process restarts.

Cancellation stops work that has not yet completed. The centered `/imports` workspace groups card
setup, content-version details, and image or folder selection in one form. Images can be dropped
onto the source picker or selected with the native image and folder dialogs. A compact activity
area beside the form on wide screens, and below it on smaller screens, shows cancellable
active jobs and the five most recent finished jobs. Complete paged queue history remains available
under `/operations`; its latest page refreshes automatically while older pages remain stable during
inspection. Failed or cancelled items can be retried through supported API and UI flows rather than
by manually editing database state. Worker claims and state transitions are designed to avoid two
workers completing the same queued item.

## Review and card history

Parser output is intentionally reviewable rather than treated as unquestionable source data. Reviewers can inspect images, parsed values, symbols, metadata matches, and suggestions before correcting the card version.

Reparsing creates new content through the card-version workflow instead of erasing historical state. See [Card management](card-management.md) for the distinction between a stable card identity and its versions.
