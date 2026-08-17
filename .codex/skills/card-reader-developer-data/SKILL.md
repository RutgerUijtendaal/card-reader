---
name: card-reader-developer-data
description: Work on Card Reader developer-data bundles and clean-checkout bootstrap. Use when changing dev-data/selection.json, dev-data.lock.json, bundle schemas or retained-version adoption, export/import validation, build workers, download grants, bootstrap scripts, publication, or developer-data UI and API behavior.
---

# Card Reader Developer Data

Follow `AGENTS.md`, `card-reader-core`, and `docs/developer-data.md`. Treat bundles as immutable, checksummed, sanitized onboarding artifacts rather than database backups.

## Publication Contract

- Keep `dev-data/selection.json` as the reviewed source of selection keys, inclusion policy, and coverage requirements.
- Keep the published catalog explicitly Player-only unless the product contract changes. Do not infer publication scope from the staff builder or from public card visibility.
- Resolve Card identity using pool plus canonical faction set. Preserve exact selected identities through groups and reject cross-pool or non-Player archive records under the current contract.
- Include only reviewed public/domain data needed by a clean checkout. Exclude accounts, decks, notifications, activity/access records, imports, uploads, OCR, parse flags, suggestions, logs, debug data, credentials, and server paths.
- Exclude TTS sheet rows, slots, coordinates, and rendered atlases. Reconcile and render fresh local sheets after import.
- Never write absolute source or server paths into a bundle.

## Schema And Compatibility

- Keep the current archive schema strict. Adopt retained immutable versions through explicit, idempotent conversion before current-schema validation.
- Preserve historical meaning when deriving missing fields. Do not make current required fields optional to accept an older bundle.
- Validate stable natural keys and code-owned classification values. Reconstruct internal identity keys instead of trusting serialized derived fields.
- Update format constants, exporter, importer, schema validation, retained-version tests, selection coverage, docs, and fixtures together.
- Never hand-edit `dev-data.lock.json`. Generate it only by publishing a fully validated immutable bundle.

## Build, Access, And Bootstrap

- Keep durable build rows as source of truth and run export/validation/publication in the dedicated builder worker.
- Validate publication through an isolated temporary import before making a version available. Production startup must never auto-import a developer bundle.
- Keep published versions immutable and retained for older pinned branches.
- Re-check active-user and Developer/staff authorization during code exchange and token-authorized download, not only when credentials are issued.
- Keep bundle creation and build history staff-only.
- Use Nginx internal redirects in production without exposing filesystem paths; preserve local `FileResponse` fallback.
- Keep destructive bootstrap reset development-only, explicit, target-checked, and preceded by a recoverable local backup.

## Implementation Workflow

1. Read `docs/developer-data.md`, selection and lock files, operations schema/exporter/importer modules, management commands, scripts, and compatibility tests.
2. State whether the change affects current output, retained input, publication selection, authorization, build orchestration, or bootstrap consumption.
3. Define the compatibility matrix before changing a bundle field or format.
4. Update validation before or with exporters so invalid archives cannot be published.
5. Exercise export, isolated import, idempotent re-import, retained-version adoption, and rejection paths relevant to the change.
6. Update the documentation and bootstrap messaging with any contract or operator-flow change.

## Hotspots And Checks

- `dev-data/selection.json`
- `dev-data.lock.json`
- `services/core/src/card_reader_core/operations/developer_data`
- `services/core/src/card_reader_core/services/developer_data`
- `services/core/src/card_reader_core/repositories/developer_data`
- `services/api/src/card_reader_api/management/commands/*dev_data*.py`
- `scripts/bootstrap-dev.py`
- `frontend/src/domain/developer-data`
- `frontend/src/features/settings/components/DeveloperDataSettingsSection.vue`

Run core and API lint/typecheck plus focused developer-data and bootstrap tests. Use a temporary output under `.tmp/dev-data/`; do not publish a production version unless the user explicitly requests it.
