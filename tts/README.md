# Tabletop Simulator Imports

This directory contains the TTS-side importer for Card Reader exports. It supports two independent flows:

- `importCardReaderDeck(...)` clones cards already present in configured TTS scripting regions by name.
- `importCardReaderCards(...)` creates `CardCustom` objects directly from Card Reader image URLs.

Both exports are base64-encoded JSON copied by the Card Reader web app. Paste `tts/importer.lua` into the TTS
Global script or another script object, then use the TTS system console or a small wrapper function to run the
matching importer.

## Requirements

- The direct-card flow requires Tabletop Simulator v14 or newer because Card Reader serves canonical WebP
  artwork. TTS added WebP support in v14.
- The Card Reader website must be reachable from every player who needs to see the cards. `localhost` works only
  for a solo game running on the same computer; multiplayer requires a shared public or LAN-reachable origin.
- When the externally visible API is mounted below a path prefix, configure its absolute base URL, for example
  `CARD_READER_PUBLIC_API_BASE_URL=https://cards.example/api`. Direct exports use this base for front and back URLs.
- A current card back must be configured in Card Reader before a direct-card export can be created.
- Direct-card exports and Gallery CSV exports require a staff account. Existing deck name exports retain the deck's
  normal public/private viewing permissions.

## Direct Card Flow

Direct exports create cards without a pre-existing TTS library or scripting region.

### Export from the Gallery

1. Open the Card Reader Gallery and choose the desired filters and sort.
2. Select `Export TTS Cards` in the filter footer.
3. The export includes every matching card, including results that have not been loaded by infinite scrolling.
4. The base64 payload is copied to the clipboard. Cards without usable latest artwork are skipped and reported.

Display-only card grouping does not change the export: the backend resolves the matching individual cards.

### Export from a content version

1. Open `Admin > Versions` and select a content version.
2. Select `Export TTS Cards` above its card gallery.
3. The export includes each distinct Card identity represented by that content version.
4. Each identity uses its current latest name and artwork URL, not a frozen historical artwork URL.

### Import into TTS

After loading `tts/importer.lua`, open the TTS system console with the backtick key and run:

```text
lua importCardReaderCards("PASTE_BASE64_HERE")
```

The importer creates individual `CardCustom` objects one at a time, waits for each card's custom assets to finish
loading, and then groups them into one named stack at `CONFIG.spawn_position`. It applies the current exported card
back to every card and stores Card Reader identity metadata in GM Notes.

If the payload is too long for the console, add a temporary wrapper to the Global script:

```lua
function importLatestCardReaderCards()
    importCardReaderCards("PASTE_BASE64_HERE")
end
```

Select `Save and Play`, then run:

```text
lua importLatestCardReaderCards()
```

### Direct-card payload

The decoded `card-reader.tts-cards.v1` payload has this shape:

```json
{
  "schema": "card-reader.tts-cards.v1",
  "collection": {
    "name": "Card Reader Gallery",
    "source": {
      "type": "gallery",
      "filters": {
        "sort": "name_asc"
      }
    }
  },
  "card_back_url": "https://cards.example/card-images/images/back-checksum.webp",
  "cards": [
    {
      "card_id": "card-id",
      "card_version_id": "version-id",
      "name": "Card Name",
      "quantity": 1,
      "front_url": "https://cards.example/cards/card-id/image",
      "image_checksum": "sha256"
    }
  ],
  "skipped": [
    {
      "card_id": "missing-card-id",
      "name": "Missing Card",
      "reason": "Card has no usable latest image."
    }
  ]
}
```

The importer honors `quantity`, so future sources such as direct deck exports can use the same schema.

Spawned cards receive GM Notes like:

```json
{
  "schema": "card-reader.tts-card.v1",
  "card_id": "card-id",
  "card_version_id": "version-id",
  "image_checksum": "sha256",
  "stable_front_url": "https://cards.example/cards/card-id/image"
}
```

## Stable artwork and TTS caching

Direct cards use this stable face URL:

```text
{verifycache}https://cards.example/cards/CARD_ID/image
```

The Card Reader endpoint always resolves to the Card's latest artwork and returns `Last-Modified`, `ETag`, and
`Cache-Control: public, no-cache`. TTS's `{verifycache}` prefix tells the game to compare the server's
`Last-Modified` value with its local mod cache and download stale artwork without changing the saved URL.

TTS performs this verification only once per game session. After publishing or promoting new Card Reader artwork:

1. Reload the TTS save/game and check the card.
2. If that TTS build does not treat the save reload as a fresh verification session, restart TTS and reopen the
   save.

There is no polling or live in-session cache eviction. Object names and GM Notes are export-time snapshots; stable
URL refresh updates the face artwork only. The card-back URL is immutable and remains the back that was current when
the export was created.

### Temporary cache-refresh test

Use this temporary public image URL to verify TTS cache refreshes without changing a Card Reader card:

```text
{verifycache}https://cards.example/tts/cache-test/card-image
```

The endpoint alternates between two distinct active card images. It reserves the next image during TTS's `HEAD`
cache check and returns that same image for the following `GET`, with a newer `Last-Modified` value for each completed
cycle. At least two active cards with distinct, readable latest images must be available.

1. Create a custom TTS card with the URL above, then save the game.
2. Reload the save and confirm that the face artwork changes.
3. Reload again and confirm that it changes back.
4. If reloading the save does not start a new cache-verification session, restart TTS and reopen the save.

This endpoint is diagnostic-only and should be removed after the supported TTS build's behavior is confirmed.

## Existing name-matching deck flow

The original flow remains available for decks that should clone cards from an existing TTS library.

1. Open a deck in Card Reader.
2. Use its `Export TTS` action for the mainboard or a sideboard.
3. Configure `CONFIG.source_region_guids` in `tts/importer.lua`.
4. Place loose source cards, decks, or bags inside those scripting regions.
5. Run:

```text
lua importCardReaderDeck("PASTE_BASE64_HERE")
```

The decoded legacy payload uses `card-reader.tts-deck.v1`:

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

The importer first uses exact normalized names, then permits a unique one-character fuzzy match. It reads names from
GM Notes JSON such as `{"name":"Hero Name"}` or falls back to the TTS nickname. Missing or ambiguous cards are
reported without stopping the remaining import. Sideboards are exported separately through their deck actions.

Use this console command to inspect the names currently available in configured source regions:

```text
lua inspectCardReaderLibrary()
```

## Implementation references

- [TTS custom game objects and `setCustomObject`](https://api.tabletopsimulator.com/custom-game-objects/)
- [TTS asset importing and persistent mod caching](https://kb.tabletopsimulator.com/custom-content/asset-importing/)
- [TTS v12 `{verifycache}` and `Last-Modified` support](https://www.tabletopsimulator.com/news/patch-notes/update-v12-0-0)
- [TTS patch notes, including v14 WebP support](https://www.tabletopsimulator.com/news/patch-notes)

TTS Lua does not expose a general-purpose worker-thread API. The name-matching flow uses `Wait.frames` batching.
The direct-card flow serializes custom-card spawns with `Object.loading_custom` and a short frame cooldown so large
imports do not trigger concurrent image downloads and decoding.
