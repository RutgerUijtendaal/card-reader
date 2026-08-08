# Tabletop Simulator Imports

This directory contains three related TTS flows:

- `importCardReaderDeck(...)` clones cards already present in configured TTS scripting regions by Card ID or name.
- `importCardReaderCards(...)` creates a native custom deck from persistent Card Reader card sheets.
- `syncCardReaderLibrary()` fetches the canonical public library and creates only missing Card identities.

Manual deck and card exports are base64-encoded JSON. The automatic library manifest is raw JSON fetched directly
by TTS. Paste `tts/importer.lua` into the TTS Global script, then invoke manual functions from the system console.

## Requirements

- The sheet flow requires Tabletop Simulator v14 or newer for WebP support.
- The Card Reader origin must be reachable by every connected player. `localhost` is suitable only for a solo game
  running on the same computer.
- Configure `CARD_READER_PUBLIC_API_BASE_URL` when the public API uses a different host or path prefix.
- Configure `CONFIG.library_manifest_url` in the Lua script when the canonical library is hosted elsewhere.
- A current Card Reader card back is required before exporting.
- Gallery and content-version TTS exports require a staff account.

## Persistent sheet flow

Card Reader assigns each usable Card a permanent position on a global 9×7 sheet. Sheets are filled in batches of 63
and stored under stable public `.webp` URLs. The current layout uses the original 822×1122 Card images without
resizing or letterboxing, producing a 7398×7854 atlas that stays within TTS's 8192-pixel texture limit on both axes.
Layout version 3 resets the test-phase sheet assignments once; assignments never move or get reused after that reset.

An export references the existing sheets containing its Cards. It does not create a compact export-specific atlas,
so a sparse selection may reference several sheets. The Lua importer combines those definitions into one native TTS
custom deck rather than spawning and grouping independent `CardCustom` objects.

### Export

- In the Gallery, choose filters and sort, then select `Export TTS Cards`. The backend includes all matching Cards,
  including unloaded pages.
- In `Admin > Versions`, select a content version and `Export TTS Cards`. Each distinct identity uses its current
  latest artwork.
- Unusable Cards are skipped and reported. The success message reports both Card and sheet counts.

### Import

Load `tts/importer.lua`, open the TTS console with the backtick key, and run:

```text
lua importCardReaderCards("PASTE_BASE64_HERE")
```

For payloads too long for the console, add a temporary wrapper to the Global script, select `Save and Play`, and
invoke the wrapper:

```lua
function importLatestCardReaderCards()
    importCardReaderCards("PASTE_BASE64_HERE")
end
```

The importer spawns one native Card for a one-Card export or one native custom Deck for larger exports. Quantities
reuse the same sheet cell. Names and Card Reader identity metadata are stored on the contained Cards.

The decoded `card-reader.tts-cards.v2` payload has this shape:

```json
{
  "schema": "card-reader.tts-cards.v2",
  "collection": {
    "name": "Card Reader Gallery",
    "source": { "type": "gallery", "filters": { "sort": "name_asc" } }
  },
  "card_back_url": "https://cards.example/card-images/images/back-checksum.webp",
  "sheets": [
    {
      "sheet_id": "sheet-id",
      "face_url": "https://cards.example/tts/card-sheets/sheet-id/image.webp",
      "columns": 9,
      "rows": 7,
      "revision": 4,
      "image_checksum": "sheet-sha256"
    }
  ],
  "cards": [
    {
      "card_id": "card-id",
      "card_version_id": "version-id",
      "name": "Card Name",
      "quantity": 1,
      "sheet_id": "sheet-id",
      "slot_index": 23,
      "image_checksum": "card-sha256",
      "lifecycle_status": "active"
    }
  ],
  "skipped": []
}
```

V1 direct-card payloads are intentionally rejected with an instruction to re-export. TTS objects previously
created from V1 remain usable but are not migrated automatically.

## Automatic library synchronization

The public canonical manifest is available without a Card Reader session:

```text
https://maityscardgame.com/api/tts/card-library/cards.json
```

It contains every usable active or deprecated Card once, using each Card's current latest version and permanent
sheet coordinate. The response uses `card-reader.tts-cards.v2` as raw JSON; manual clipboard exports remain base64.

The relevant Lua configuration defaults are:

```lua
auto_sync_enabled = true
library_manifest_url = "https://maityscardgame.com/api/tts/card-library/cards.json"
auto_sync_retry_delays = { 2, 5, 15, 30 }
library_batch_spacing = 3
```

With `auto_sync_enabled = true`, Global `onLoad()` fetches the manifest, scans `source_region_guids` over multiple
frames, and compares immutable Card IDs stored in GM Notes. Only missing identities are spawned. Each update is a
separate native Card or Deck positioned beside existing batches in the first valid configured region; batches are
not regrouped. Rotated regions are supported, and synchronization stops instead of spawning outside the region when
its batch slots are full. The configured scripting region should therefore be reserved for the Card Reader library.
Manual card and deck imports continue to use `spawn_position`; that player-facing location is not used by autosync.

Set `auto_sync_enabled = false` to disable startup requests and automatic retries. Manual synchronization remains
available while disabled:

```text
lua syncCardReaderLibrary()
```

If the game already has a Global `onLoad()`, keep that handler and call `startCardReaderLibraryAutoSync()` from it
instead of defining a second `onLoad()`. Request failures, HTTP 429 responses, and server errors use the configured
bounded retry delays; a manual call starts a fresh retry sequence.

Synchronization is additive. It never removes Cards, combines update batches, rewrites existing objects, or polls
during a live session. Exact unique names prevent duplicate creation for legacy objects without Card Reader GM
Notes, but those matches are reported as legacy. Duplicate Card IDs and server-skipped images are also reported.
Existing names, lifecycle metadata, and GM Notes remain snapshots; stable sheet artwork refreshes on reload as
described below. Each separate batch keeps the immutable card back current when that batch was created.

## Artwork refresh and caching

TTS receives each face URL with the verification prefix:

```text
{verifycache}https://cards.example/tts/card-sheets/SHEET_ID/image.webp
```

When a Card's latest artwork changes, Card Reader marks its sheet dirty. The background sheet renderer coalesces
nearby changes, rebuilds the atlas atomically, and publishes a new `ETag` and monotonically newer `Last-Modified`
value at the same URL. Internally, each published atlas uses a checksum-versioned filename: the renderer finishes
that immutable file before switching the database metadata, so requests cannot receive new bytes with stale cache
headers. Garbage collection retains the current revision and one prior revision for in-flight requests while
removing older files, which bounds runtime and backup growth.

TTS verifies an asset once per game session. After publishing or promoting artwork:

1. Wait for the sheet renderer to publish the update.
2. Reload the TTS save/game.
3. If the installed build does not treat save reload as a fresh verification session, restart TTS and reopen the
   save.

There is no live-session polling or object rewriting. Names and GM Notes remain export-time snapshots. The exported
card-back URL is immutable and remains the back that was current at export time.

### Sheet operations

Production and local development run `run_tts_sheet_renderer` as a separate process using the existing API image.
Renderer startup releases expired claims left by an interrupted previous process before reconciling sheet state;
live leases from an overlapping renderer are preserved. Render completion also verifies the exact lease before it
can publish metadata. A graceful shutdown releases a claim acquired immediately before the stop request.
Useful maintenance commands are:

```text
python manage.py reconcile_tts_card_sheets
python manage.py reconcile_tts_card_sheets --render
python manage.py reconcile_tts_card_sheets --force --render
python manage.py run_tts_sheet_renderer --once
```

Developer-data bundles contain Card records and immutable Card images, not TTS sheet records or atlases. Import and
bootstrap assign fresh local sheet IDs and render fresh atlases from those imported images. Production sheet IDs and
coordinates are therefore not reproduced in a developer-data checkout.

Runtime backups may include rendered atlases. Restore keeps only files whose SHA-256 matches the sheet state in the
database snapshot; missing or mismatched atlases are rebuilt by the renderer after startup.

### Temporary cache-refresh test

The temporary diagnostic endpoint remains available while cache behavior is being verified:

```text
{verifycache}https://cards.example/tts/cache-test/card-image
```

It alternates between two distinct readable active Card images. Save a custom Card using that URL, reload twice, and
confirm that its face alternates. Restart TTS if save reload does not start a new verification session.

## Existing name-matching deck flow

The original flow remains available for decks that clone an existing TTS library:

1. Export TTS from a Card Reader deck or sideboard.
2. Configure `CONFIG.source_region_guids`.
3. Place loose Cards, decks, or bags inside those scripting regions.
4. Run `lua importCardReaderDeck("PASTE_BASE64_HERE")`.

It uses `card-reader.tts-deck.v1` and now includes optional Card IDs. The importer resolves Card IDs first, then
retains exact normalized names and unique one-character fuzzy matches for older exports or library objects. It
reports missing or ambiguous Cards without stopping the remaining import. Use
`lua inspectCardReaderLibrary()` to list names available in configured regions.

## References

- [TTS custom deck/card Lua API](https://api.tabletopsimulator.com/custom-game-objects/)
- [TTS custom deck sheets](https://kb.tabletopsimulator.com/custom-content/custom-deck/)
- [TTS asset importing and mod caching](https://kb.tabletopsimulator.com/custom-content/asset-importing/)
- [TTS v12 `{verifycache}` support](https://www.tabletopsimulator.com/news/patch-notes/update-v12-0-0)
- [TTS patch notes, including v14 WebP support](https://www.tabletopsimulator.com/news/patch-notes)
