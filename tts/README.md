# Tabletop Simulator Import

This directory contains the TTS-side importer for deck exports produced by the Card Reader frontend.

## Current Flow

1. Open a deck in Card Reader.
2. Use the `Export TTS` button next to the deck view options.
3. Save the downloaded `.tts.txt` file or copy its base64 contents.
4. Open Tabletop Simulator.
5. Paste `tts/importer.lua` into the Global script or another script object.
6. Configure the source scripting regions in `CONFIG.source_region_guids`.
7. Run `importCardReaderDeck("...base64...")` inside TTS.

## Access Rules

- TTS deck export is allowed for any viewer who can open the deck detail page.
- Public decks can therefore be exported by anyone.
- Private decks can only be exported by their owner.
- This intentionally differs from the gallery CSV export, which remains staff-only.

## What The Export Contains

The exported payload is a base64-encoded JSON object with this shape:

```json
{
  "schema": "card-reader.tts-deck.v1",
  "deck": {
    "name": "Deck Name",
    "description": "Optional description"
  },
  "hero": {
    "role": "hero",
    "quantity": 1,
    "name": "Hero Name"
  },
  "cards": [
    {
      "role": "mainboard",
      "quantity": 4,
      "name": "Card Name"
    }
  ]
}
```

Current importer behavior:
- `cards` is the mainboard import list.
- Sideboard entries are not exported because `tts/importer.lua` imports only the hero and mainboard cards.
- Export quantities are kept as counted import requests. The importer resolves
  each unique card name once, then spawns the requested number of copies from
  the cached source data.
- Spawned cards use the same `x`/`z` coordinates and a small increasing
  `y` offset, creating a vertical stack at `CONFIG.spawn_position`.
- After all spawn callbacks finish, the importer waits briefly for TTS to
  settle the stack, then names and describes the live stack or deck near
  `CONFIG.spawn_position`.
- Large imports are processed in small frame-scheduled batches so TTS can keep
  updating the UI between chunks.
- Missing cards are logged to the TTS console and do not stop the rest of the
  import.

TTS Lua does not expose a general-purpose worker thread API for scripts. The
importer uses `Wait.frames` batching instead, which is the practical way to
avoid doing all clone/index/spawn work in a single blocking frame.

## How The Lua Importer Matches Cards

The importer searches cards in the configured source scripting regions by card
name. Put loose source cards, decks, or bags inside those regions before
running the import.
It first tries an exact normalized name match. If that fails, it falls back to
one-character fuzzy name matching, which allows one missing or different
character. Fuzzy matching only succeeds when exactly one source card matches;
ambiguous fuzzy matches are treated as missing cards.

Supported name sources:

- `GMNotes` JSON such as `{"name":"Hero Name"}`
- exact TTS card nickname/name fallback

## Example TTS Setup

Set the source scripting regions first:

```lua
local CONFIG = {
    source_region_guids = {
        "abc123",
        "def456",
    },
    spawn_position = { x = -45, y = 3, z = 50 },
}
```

Then import:

```lua
importCardReaderDeck("PASTE_BASE64_HERE")
```

## How To Actually Run It In TTS

There are two practical ways to execute the import function after `tts/importer.lua` is loaded into the Global script.

### Option 1: System Console

1. Load the Lua script into the Global script in the TTS scripting editor.
2. Click `Save and Play` so TTS reloads the script.
3. Open the TTS system console with the backtick key.
4. Run:

```text
lua importCardReaderDeck("PASTE_BASE64_HERE")
```

This executes the Lua call against the current mod after the script has been loaded.

### Option 2: Temporary Wrapper Function

If the base64 payload is too long to paste comfortably into the console, add a small helper in the Global script:

```lua
function importLatestDeck()
    importCardReaderDeck("PASTE_BASE64_HERE")
end
```

Then `Save and Play`, open the system console, and run:

```text
lua importLatestDeck()
```

This is usually the easier option for long payloads.

To inspect what the importer can currently match:

```lua
inspectCardReaderLibrary()
```

## Notes

- The importer clones from card object data already present in the TTS save.
- It does not create custom cards from image URLs.
- Source cards must be inside a configured scripting region. Loose cards,
  decks, and bags inside the region are supported.
- Name-only matching depends on the exported Card Reader names matching the TTS card names closely.
