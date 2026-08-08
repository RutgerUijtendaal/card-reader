# Tabletop Simulator importer

Card Reader uses one website-to-TTS import flow for decks, sideboards, gallery selections, and content versions.
Every export is a Base64-encoded `card-reader.tts-cards.v2` payload that references persistent Card Reader sheet
atlases. The scripted importer creates a native TTS custom deck directly from those sheets; it does not require a
preloaded card library or scripting regions.

## Install the importer object

1. Create or choose a TTS object that will host the importer controls.
2. Open **Modding → Scripting** and select that object.
3. Copy `tts/importer.lua` into the object's Lua script.
4. Choose **Save & Play**.
5. Save the scripted object through **Objects → Saved Objects** when it should be reusable in other games.

The object creates one text input and one **Import** button. Keep the script attached to an object rather than
Global: its `onLoad()` callback uses `self.createInput` and `self.createButton`.

## Import an export

1. Use a TTS export action on a deck, sideboard, gallery, or content version in Card Reader.
2. Paste the copied Base64 string into the importer object's text input.
3. Press **Import**.

The importer validates the v2 payload, reports server-skipped cards in the TTS console, and spawns the collection
at `CONFIG.spawn_position`. Legacy `card-reader.tts-deck.v1` and `card-reader.tts-cards.v1` strings are rejected with
an instruction to re-export them.

## Payload contract

All website exports share this shape:

```json
{
  "schema": "card-reader.tts-cards.v2",
  "collection": {
    "name": "Example collection",
    "description": "Optional deck description",
    "source": {
      "type": "deck"
    }
  },
  "card_back_url": "https://cards.example/card-images/back.webp",
  "sheets": [
    {
      "sheet_id": "sheet-id",
      "face_url": "https://cards.example/tts/card-sheets/sheet-id/image.webp",
      "columns": 9,
      "rows": 7,
      "revision": 4,
      "image_checksum": "sheet-checksum"
    }
  ],
  "cards": [
    {
      "card_id": "card-id",
      "card_version_id": "version-id",
      "name": "Card name",
      "quantity": 4,
      "role": "mainboard",
      "sheet_id": "sheet-id",
      "slot_index": 12,
      "image_checksum": "image-checksum",
      "lifecycle_status": "active"
    }
  ],
  "skipped": []
}
```

`collection.description` and `cards[].role` are optional so gallery and version exports remain compatible. Deck
exports store an export-time source snapshot with the deck ID, scope, hero ID, difficulty, tags, and optional
sideboard identity. The imported deck receives the collection name and description plus structured collection GM
Notes. Each card receives Card Reader identity GM Notes and its optional `hero`, `mainboard`, or `sideboard` role.

Deck exports keep the hero and mainboard in one native deck. Targeted sideboard exports contain only that sideboard.
The hero is required for a main-deck export; unavailable non-hero cards are included in `skipped` with their saved
quantity and role.

An export references the persistent sheets that already contain its Cards. It does not create a compact
export-specific atlas, so a sparse selection may reference several sheets.

## Artwork refresh and caching

TTS receives each face URL with the verification prefix:

```text
{verifycache}https://cards.example/tts/card-sheets/SHEET_ID/image.webp
```

When a Card's latest artwork changes, Card Reader marks its sheet dirty. The background renderer coalesces nearby
changes, builds a checksum-versioned atlas, validates it, and atomically publishes new metadata at the stable sheet
URL. Requests made while rendering continue to receive the previous complete revision; they never receive partial
new bytes or mismatched cache headers. The current and one prior file revision are retained for in-flight requests.

TTS verifies an asset once per game session. After publishing artwork:

1. Wait for the sheet renderer to publish the update.
2. Reload the TTS save/game.
3. If the installed TTS build does not treat reload as a fresh verification session, restart TTS and reopen the
   save.

There is no live-session polling or automatic object rewriting. Names, descriptions, roles, and GM Notes remain
export-time snapshots.

## Sheet operations

Production and local development run `run_tts_sheet_renderer` as a separate process using the API image. Useful
maintenance commands are:

```text
python manage.py reconcile_tts_card_sheets
python manage.py reconcile_tts_card_sheets --render
python manage.py reconcile_tts_card_sheets --force --render
python manage.py run_tts_sheet_renderer --once
```

Renderer startup releases expired claims while preserving live leases. Publication verifies the exact claim before
switching metadata. Developer-data imports reconcile and render fresh local sheets because bundles contain Card
records and immutable images, not TTS sheet assignments or atlases.

Persistent sheet slots are append-only. Do not compact, reorder, delete, or reuse coordinates after publication.
Merged Card identities retain their original slots and resolve to the surviving Card.

## References

- [TTS scripting overview](https://api.tabletopsimulator.com/overview/)
- [TTS custom deck sheets](https://kb.tabletopsimulator.com/custom-content/custom-deck/)
- [TTS saved objects](https://kb.tabletopsimulator.com/host-guides/spawning-objects/)
