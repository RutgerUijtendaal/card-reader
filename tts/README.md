# Tabletop Simulator Import

This directory contains the TTS-side importer for deck exports produced by the Card Reader frontend.

## Current Flow

1. Open a deck in Card Reader.
2. Use the `Export TTS` button next to the deck view options.
3. Save the downloaded `.tts.txt` file or copy its base64 contents.
4. Open Tabletop Simulator.
5. Paste `tts/importer.lua` into the Global script or another script object.
6. Configure the source card containers in `CONFIG.source_container_guids`.
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
    "id": "deck-id",
    "name": "Deck Name",
    "description": "Optional description",
    "total_cards": 60,
    "unique_cards": 15
  },
  "lookup": {
    "preferred_keys": ["card_id", "card_key", "name"]
  },
  "hero": {
    "role": "hero",
    "quantity": 1,
    "card_id": "hero-id",
    "card_key": "hero-key",
    "name": "Hero Name"
  },
  "cards": [
    {
      "role": "mainboard",
      "quantity": 4,
      "card_id": "card-id",
      "card_key": "card-key",
      "name": "Card Name"
    }
  ],
  "sideboards": [
    {
      "name": "Tech",
      "cards": [
        {
          "role": "sideboard",
          "quantity": 2,
          "card_id": "sideboard-card-id",
          "card_key": "sideboard-card-key",
          "name": "Sideboard Card Name"
        }
      ]
    }
  ]
}
```

Current importer behavior:
- `cards` is the mainboard import list.
- `sideboards` is exported for future use and is currently ignored by `tts/importer.lua`.

## How The Lua Importer Matches Cards

The importer searches cards in the configured source containers and matches in this order:

1. `card_id`
2. `card_key`
3. `name`

Best results come from storing Card Reader identifiers in TTS card metadata.

Supported metadata sources:

- `GMNotes` JSON such as `{"card_id":"...","card_key":"...","name":"..."}`
- tagged lines like `card_reader_id: ...`
- tagged lines like `card_reader_key: ...`
- exact card name fallback

## Example TTS Setup

Set the source containers first:

```lua
local CONFIG = {
    source_container_guids = {
        "abc123",
        "def456",
    },
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
- If your cards are loose on the table instead of inside bags/decks, the importer will need to be adapted.
- Name-only matching is fragile. Prefer `card_id` or `card_key`.
