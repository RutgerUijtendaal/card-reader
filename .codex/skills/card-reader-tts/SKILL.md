---
name: card-reader-tts
description: Work on Card Reader's persistent Tabletop Simulator card-sheet and export system. Use when changing TTS sheet models, slot assignment, renderer claims and publication, sheet image caching, deck/sideboard/gallery/content-version exports, the card-reader.tts-cards.v2 payload, or tts/importer.lua.
---

# Card Reader TTS

Follow `AGENTS.md`, `card-reader-core`, and `tts/README.md`. Treat the website's persistent sheets as the sole source for TTS card artwork; do not introduce compact per-export atlases or library/name synchronization.

## Persistent Sheet Invariants

- Partition sheets by `card_pool`; never mix Player, Evil, and Neutral slots on one sheet.
- Keep sheet image URLs stable and public. Publish checksum-versioned files behind stable metadata and cache headers.
- Treat slot assignments as append-only. Never compact, reorder, delete, or reuse a published coordinate.
- Preserve source slots across Card merges and resolve them to the surviving Card.
- Mark affected sheets dirty when current artwork changes. Continue serving the previous complete revision while rendering.
- Verify the exact live claim before publication, publish metadata atomically, and retain the current and one prior file revision for in-flight requests.
- Release expired claims without stealing live leases; keep renderer work coalesced through durable sheet rows rather than adding a broker.

## Export Contract

- Emit the shared Base64 `card-reader.tts-cards.v2` payload for decks, sideboards, Gallery selections, and content versions.
- Reference existing persistent sheets and slots. Do not create export-specific sheet assignments.
- Preserve saved deck quantities and order, export-time source metadata, and optional `hero`, `mainboard`, or `sideboard` roles.
- Include deprecated Cards still referenced by decks. Report unavailable cards in `skipped` with quantity and role.
- Require usable hero artwork for main-deck exports; keep targeted sideboard exports independent.
- Keep direct sheet images public. Preserve endpoint-specific authorization for export creation and deck visibility.

## Importer Contract

- Keep `tts/importer.lua` attached to an object and spawn native custom decks directly from payload sheets.
- Reject legacy v1 schemas with a re-export instruction.
- Preserve Card Reader identity and collection metadata in GM Notes.
- Keep `{verifycache}` face URLs and document that artwork refresh becomes visible after a fresh TTS verification session.

## Developer Data And Operations

- Keep TTS rows, slots, coordinates, and atlases out of developer-data bundles.
- Reconcile and optionally render fresh local sheets after developer-data import.
- Run `run_tts_sheet_renderer` as a separate polling worker using the shared database and storage contract.
- Keep maintenance reconciliation idempotent; `--force --render` must not alter slot identity.

## Implementation Workflow

1. Trace the model, repository, service, renderer, API export builder, frontend response handling, and Lua importer for the affected contract.
2. Define slot identity, claim ownership, authoritative publication success, cache behavior, and cleanup semantics before changing renderer state.
3. Keep payload schema changes synchronized across Python serialization, TypeScript handling, Lua validation/spawning, tests, and `tts/README.md`.
4. Cover pool partitioning, merge behavior, stale claims, failed renders, atomic publication, previous-revision serving, quantities/roles, deprecated cards, and authorization as applicable.
5. Run core/API/frontend checks plus focused TTS tests. Validate Lua syntax or exercise the importer path when `tts/importer.lua` changes.

## Hotspots

- `services/core/src/card_reader_core/models/tts_card_sheet.py`
- `services/core/src/card_reader_core/repositories/tts_card_sheets`
- `services/core/src/card_reader_core/services/tts_card_sheets`
- `services/api/src/card_reader_api/cards/tts_card_sheets.py`
- `services/api/src/card_reader_api/exports/tts_cards.py`
- `services/api/src/card_reader_api/management/commands/*tts*.py`
- `frontend/src/domain/cards/composables/useTtsCardExport.ts`
- `frontend/src/domain/cards/utils/ttsExportResponse.ts`
- `tts/importer.lua`
