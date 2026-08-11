# Deck Building

Deck building combines card selection with core-owned rules so the editor, API, exports, and Playtester agree on whether a deck is valid.

## Deck structure and visibility

A deck can contain a hero, a mainboard, and supported sideboard sections. Entries reference stable card identities and store quantities rather than copying card content into the deck.

All referenced cards must belong to the Player pool. The selected hero must also have the Hero role, and Hero-role cards remain excluded from ordinary mainboard entries under the existing rules. Deck-builder searches send the Player pool explicitly and use role filters rather than a card boolean.

The current deck model and builder are therefore the **Player deck** workflow. Decks do not yet persist their own Player/Game Master classification. A later deck-design project is expected to classify stable deck identities explicitly, but it must define Game Master deck structure and validation on their own terms instead of assuming the current hero/mainboard/sideboard shape applies.

Deck list predicates and embedded card payloads receive an explicit card-pool visibility scope. Ordinary owners retain restricted placeholders with secret-keyed opaque identifiers and a generic invalid state for reclassified references, while staff can inspect the original card content. Exact unchanged placeholder sections may round-trip through an update so unrelated edits preserve server-owned restricted references; changed opaque references are rejected, while omitting a restricted entry still removes it. Deck creation, normalization, validation, TTS export, and Playtester eligibility remain fixed to the Player-only scope; staff access to Game Master cards does not turn the current deck workflow into a Game Master deck workflow. Playtester eligibility depends on every referenced card remaining active and in the Player pool, not on general deck validity, so under-construction Player decks remain available for experimentation while decks with deprecated references stay outside the normal play surface. TTS export applies that pool boundary to the requested board: a restricted sideboard does not block a Player mainboard or a different Player sideboard export. Export authorization checks ownership or public/unlisted visibility before the requested board, without applying unrelated whole-deck validity; private decks remain owner-only.

A future **Scenario** sits above ordinary decks rather than turning a deck into a mixed-pool container. The intended direction is that a scenario can reference Player decks together with Game Master Boons, Events, Locations, and other scenario material, potentially through groups. Its exact schema, ownership, cardinalities, and authoring flow remain deliberately undecided.

Decks are owned by users and may be private or publicly listed according to their visibility state. List surfaces use compact summary records; detail, editing, export, and playtest flows load the full deck only when board entries are required.

## Local-first creation

New decks remain unpublished browser drafts until the owner explicitly selects **Create**. Hero, Details, and Cards are peer editor screens during this phase, and autosync remains unavailable because no server deck exists yet.

One versioned draft is stored per authenticated user. It includes the complete form, board ordering and quantities, sideboards, and snapshots of referenced cards. On recovery, snapshots are shown immediately while current cards, merged identities, tags, ordering, and quantities are reconciled before editing resumes. Browser storage is best-effort: if it is unavailable, the in-memory draft and leave warning remain active, but a confirmed server creation is never reversed or blocked by browser cleanup.

Each unpublished draft has a stable UUID. Create sends that UUID as an owner-scoped idempotency key, so a retry returns the same deck instead of creating a duplicate. A durable creation record retains used keys after deck deletion, allowing retries and lookups to report the deleted outcome without recreating the deck. If the initial response is ambiguous, the editor reconciles the UUID with delayed retries; a found deck completes navigation, a deleted result retires the stale local attempt, and repeated misses or unavailable lookups keep the exact attempted payload locked for a safe Retry. A miss unlocks the draft only when the failed Create returned a definitive HTTP response.

Conditional storage revisions and an owner-scoped browser lock make each compare-and-write mutation atomic across tabs. Browsers without that lock support retain the draft in memory instead of risking an overwrite. When another tab changes, removes, or creates the same draft, persistence and Create pause until the user explicitly loads the stored draft, keeps the current tab, discards it, opens the created deck, or keeps the contents under a new draft UUID.

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

If a card in an existing deck becomes deprecated, loses the Hero role while selected as the hero, or moves to the Game Master pool, the reference is retained. The deck then shows a warning or invalid public-listing state rather than losing an entry without the owner's involvement. Non-staff owners see a restricted placeholder instead of embedded Game Master card content, while retaining enough deck context to remove or replace the reference.

## Related features

Player decks can be exported and opened in the [Playtester](playtester.md). Game Master deck behavior and scenario composition remain deferred. Card identity, lifecycle, and per-card configuration are described in [Card management](card-management.md).
