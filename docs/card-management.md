# Card Management

Card management separates a card's stable identity from the content extracted or edited at a particular point in time. That distinction lets the application retain history, repair parsing results, group related printings, and safely consolidate duplicates.

## Cards and versions

A `Card` is the durable identity referenced by decks, groups, aliases, and application URLs. A `CardVersion` contains versioned content such as parsed text, images, template selection, symbols, and metadata relations.

Each card points to its current version, while older versions remain available for history and comparison. Imports, reparses, and edits use this version model so a correction does not destroy the record of what existed previously.

Content versions provide an additional history boundary for related changes made during import and editing workflows. The UI exposes this history through card detail and generation views.

## Pool and roles

Every stable card identity belongs to either the **Player** or **Game Master** pool. A card can also hold any combination of the code-owned Hero, Boon, and Event roles. **Standard** is the displayed name for a card with no role assignments; it is derived rather than stored.

Staff edit both dimensions in the Card tab alongside lifecycle state and deck-building configuration. They are intentionally independent of template selection, which remains version-level parsing configuration. The Admin Catalog shows the pool plus every assigned role, or Standard, on linked-card and suggestion tiles.

Card collections accept a pool plus role inclusion/exclusion filters with `any` or `all` matching. The ordinary Gallery starts in the Player pool with Hero excluded to keep its default browsing view focused. Staff can explicitly switch the Gallery filter to Game Master cards. Imports require an explicit pool and default to automatic multi-role inference from snapshotted template hints and stable metadata signals; workspace-level navigation remains a separate future workflow.

Import classification initializes only new card identities. Existing cards and reparses retain their authoritative Card-tab pool and roles. A differing inferred result completes with an ordered warning and audit evidence instead of silently reclassifying the card.

## Metadata and aliases

Card versions connect parsed content to managed catalogs such as card types, keywords, tags, symbols, and metadata groups. These relationships power filtering, display, rules text, and deck-building behavior.

Aliases provide alternate names or identifiers for the same card identity. They support matching and redirects without creating duplicate cards solely because an import used a different spelling or historical name.

### Mana families

The application owns six canonical mana families in a fixed release-time order: Arcane, Dark, Divine, Martial, Occult, and Primal. Each family's mana symbol and paired affinity symbol are aliases for the same family. The legacy `primla-affinity` symbol key remains readable as Primal for existing data, but APIs and UI state use `primal-affinity`.

`CardVersion.mana_family_sort_key` stores an indexed rank derived from the version's linked symbols. Single-family cards use the six family ranks. Multitype cards follow them in lexicographic family-tuple order, and numeric colorless symbols, unmatched named affinities, and cards without a canonical symbol share the final no-family bucket. Replacing, renaming, or deleting linked symbols refreshes the stored rank so gallery queries can sort before pagination without deriving it per result.

Card gallery APIs expose `sort=mana_type_asc` and canonical filters through repeated `mana_family_keys` and `mana_family_exclude_keys` parameters plus `mana_family_match=any|all`. A canonical filter matches either the mana or affinity representation. Existing mana- and affinity-symbol parameters remain literal and backward compatible. `GET /cards/filters` supplies the ordered `mana_families` catalog used by gallery filters, deck-builder hero selection, and hero-derived deck presets; unmatched affinities remain available in the separate Affinity filter.

## Lifecycle state

Cards have an explicit lifecycle state:

- Active cards appear by default in gallery, public group views, catalog previews, exports, deck building, and Playtester selection.
- Deprecated cards remain directly retrievable and available in explicit management queries, but are hidden from ordinary browsing and selection.

Deprecating or reclassifying a card does not silently remove it from existing decks or groups. Those relationships remain visible so owners can resolve them deliberately. Deck validation and management views surface the resulting warnings or invalid state, while restricted Game Master card content is redacted from non-staff embedded deck payloads.

## Card groups

Groups collect related card identities, such as alternate printings or variants, in an intentional order. Every group has an active anchor card that acts as its primary public identity.

Deprecated non-anchor members may remain attached for administrative history but are omitted from active public group views. Changing group membership or order is handled through the group service so anchor and lifecycle invariants remain consistent.

## Merging duplicates

Merging consolidates duplicate card identities while preserving useful history. The merge workflow moves compatible versions, aliases, metadata relationships, group membership, and other references to the surviving card. Old identifiers can redirect to the survivor instead of becoming broken links.

Merges are domain operations, not raw row deletion. Conflict checks and a preview step allow staff to understand the result before committing a merge.

## Ownership boundaries

API views handle authorization, request validation, and response formatting. They translate the viewer capability into `CardPoolScope` once and pass that visibility value into card-derived repositories, services, and payload builders. Core code does not inspect users or staff state. Card, card-group, catalog, deck, image, and export queries apply the scope before search, counts, ordering, previews, or aggregation, while unrestricted persistence helpers remain deliberate administrative/domain operations.

This separation keeps imports, staff tools, deck building, and future clients aligned on the same card behavior.
