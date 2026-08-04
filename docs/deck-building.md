# Deck Building

Deck building combines card selection with core-owned rules so the editor, API, exports, and Playtester agree on whether a deck is valid.

## Deck structure and visibility

A deck can contain a hero, a mainboard, and supported sideboard sections. Entries reference stable card identities and store quantities rather than copying card content into the deck.

Decks are owned by users and may be private or publicly listed according to their visibility state. List surfaces use compact summary records; detail, editing, export, and playtest flows load the full deck only when board entries are required.

## Constraint model

The backend exposes the current constraint definitions through `GET /decks/rules`. The frontend uses that response for limits, descriptions, examples, and action behavior, retaining local defaults only as load-error resilience.

Supported rules currently include:

- `mainboard_copy_limit`
- `mainboard_card_count`
- `mana_type_count`
- `legendary_copy_limit`
- `sideboard_entry_quantity`

Rules carry three important behaviors:

- Severity is `hard` or `soft`. Hard violations affect validity; soft violations warn without invalidating the deck.
- Scope is `mainboard` or `whole_deck`, determining which entries contribute to the rule.
- A hard rule may set `blocks_action`, allowing the editor and API to prevent an addition that would exceed the limit.

## Card-specific overrides

Individual cards can alter supported constraints through their deck-building configuration. Hero cards use the same override mechanism as other cards, which allows future card-driven rules without introducing a separate hero-only rules engine.

Overrides are interpreted and validated by core services. Clients should display the resulting rules, not independently infer behavior from card text.

## Validation and lifecycle

The API validates submitted deck changes against the same rule model exposed to the frontend. This keeps direct API requests and interactive editor actions consistent.

If a card in an existing deck becomes deprecated, the reference is retained. The deck can then show a warning or invalid public-listing state rather than losing an entry without the owner's involvement.

## Related features

Decks can be exported and opened in the [Playtester](playtester.md). Card identity, lifecycle, and per-card configuration are described in [Card management](card-management.md).

