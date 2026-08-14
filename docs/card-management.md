# Card Management

Card management separates a card's stable identity from the content extracted or edited at a particular point in time. That distinction lets the application retain history, repair parsing results, group related printings, and safely consolidate duplicates.

## Cards and versions

A `Card` is the durable identity referenced by decks, groups, aliases, and application URLs. A `CardVersion` contains versioned content such as parsed text, images, template selection, symbols, and metadata relations.

Each card points to its current version, while older versions remain available for history and comparison. Imports, reparses, and edits use this version model so a correction does not destroy the record of what existed previously.

Content versions provide an additional history boundary for related changes made during import and editing workflows. The UI exposes this history through card detail and generation views.

## Pool, roles, and factions

Every stable card identity belongs to exactly one of the **Player**, **Evil**, or **Neutral** pools. Neutral is currently a separate pool rather than an implicit overlay in Player or Evil views. A card can also hold any combination of the code-owned Hero, Boss, Location, Boon, Event, and Shop Item roles, plus any combination of the Order, Blood, and Darkness factions. **Normal** is the displayed name for a card with no role assignments; it is derived rather than stored. A Normal card may still have factions.

Role and faction keys allow up to 64 characters. Their definitions, labels, and ordering are code-owned. Hero remains the only role with existing deck-builder or Playtester behavior; every other role and all factions are descriptive until their gameplay rules are designed.

Staff edit all three dimensions in the Card tab alongside lifecycle state and deck-building configuration. They are intentionally independent of template selection, which remains version-level parsing configuration. The Admin Catalog and reusable staff card-search rows show the pool, roles or Normal, and factions or No faction as visually distinct badge groups.

Admin Catalog and Review are global staff operational surfaces. They query every card pool authorized for the current staff user regardless of the Player/Evil/Neutral shell workspace. Their mixed-pool counts, queues, searches, suggestions, and previews always retain visible pool classification so duplicate names remain distinguishable.

Card collections accept one pool plus independent role and faction inclusion/exclusion filters with `any` or `all` matching. Player, Evil, and Neutral are primary site workspaces selected from the sidenav; the active workspace supplies the Gallery pool and is serialized in shareable Gallery URLs. Player is the safe default, while Evil and Neutral options appear only when the session's ordered pool scope permits them. Every workspace starts with Hero excluded, no faction defaults, and no implicit Neutral overlay. Filter choices remain unconditional until the later pool-aware filter redesign. Switching workspaces keeps global staff and settings routes mounted, resets Gallery to the selected pool's canonical defaults, and keeps card or group resources open while updating their Gallery return context. Player-only deck and Playtester routes fall back to the selected restricted Gallery only when they cannot remain active. Imports require an explicit pool, use the active workspace as a pristine editable default, and default to independent automatic role and faction inference from snapshotted template hints and stable metadata signals.

Import classification initializes only new card identities. Untargeted imports resolve factions before matching latest image hashes, primary names, and aliases inside the selected pool and exact canonical faction set. The same name or artwork may therefore represent independent cards in different pools or faction namespaces. Existing cards in the matched namespace and targeted reparses retain their authoritative Card-tab pool, roles, and factions. A differing inferred role result after an untargeted match, or any differing targeted-reparse classification, completes with an ordered warning and audit evidence instead of silently reclassifying the card.

## Metadata and aliases

Card versions connect parsed content to managed catalogs such as card types, keywords, tags, symbols, and metadata groups. These relationships power filtering, display, rules text, and deck-building behavior.

Aliases provide alternate names or identifiers for the same card identity. Primary and alias keys share a namespace scoped by pool plus the card's exact canonical faction set. The same normalized key may exist independently in another pool or faction namespace. Rename, pool, and faction edits validate the complete destination namespace and move the primary name, every alias, and faction assignments atomically. One durable lock row per pool serializes primary and alias mutations across imports, edits, merges, and developer-data adoption.

### Mana families

The application owns six canonical mana families in a fixed release-time order: Arcane, Dark, Divine, Martial, Occult, and Primal. Each family's mana symbol and paired affinity symbol are aliases for the same family. The legacy `primla-affinity` symbol key remains readable as Primal for existing data, but APIs and UI state use `primal-affinity`.

`CardVersion.mana_family_sort_key` stores an indexed rank derived from the version's linked symbols. Single-family cards use the six family ranks. Multitype cards follow them in lexicographic family-tuple order, and numeric colorless symbols, unmatched named affinities, and cards without a canonical symbol share the final no-family bucket. Replacing, renaming, or deleting linked symbols refreshes the stored rank so gallery queries can sort before pagination without deriving it per result.

Card gallery APIs expose `sort=mana_type_asc` and canonical filters through repeated `mana_family_keys` and `mana_family_exclude_keys` parameters plus `mana_family_match=any|all`. A canonical filter matches either the mana or affinity representation. Existing mana- and affinity-symbol parameters remain literal and backward compatible. `GET /cards/filters` supplies the ordered `mana_families` catalog used by gallery filters, deck-builder hero selection, and hero-derived deck presets; unmatched affinities remain available in the separate Affinity filter.

## Lifecycle state

Cards have an explicit lifecycle state:

- Active cards appear by default in gallery, public group views, catalog previews, exports, deck building, and Playtester selection.
- Deprecated cards remain directly retrievable and available in explicit management queries, but are hidden from ordinary browsing and selection.

Deprecating or reclassifying a card does not silently remove it from existing decks or groups. Those relationships remain visible so owners can resolve them deliberately. Deck validation and management views surface the resulting warnings or invalid state, while Evil and Neutral card content is redacted from non-staff embedded deck payloads.

## Card groups

Groups collect related card identities, such as alternate printings or variants, in an intentional order. Every group has an active anchor card that acts as its primary public identity.

Groups may intentionally span pools. Public payloads include only members the viewer is authorized to access; staff can see and manage permitted cross-pool members. Linked members retain their own pool classification, show a pool badge when it differs from the active workspace, and preserve the originating workspace for return navigation. The group route uses the anchor's pool rather than borrowing the source card's pool.

Deprecated non-anchor members may remain attached for administrative history but are omitted from active public group views. Changing group membership or order is handled through the group service so anchor and lifecycle invariants remain consistent.

## Merging duplicates

Merging consolidates duplicate card identities while preserving useful history. The merge workflow moves compatible versions, aliases, metadata relationships, group membership, and other references to the surviving card. Old identifiers can redirect to the survivor instead of becoming broken links.

Merges are domain operations, not raw row deletion. Conflict checks and a preview step allow staff to understand the result before committing a merge. Cross-pool and cross-faction-namespace merges are rejected; staff must explicitly reclassify a source first when that is intentional. Same-namespace merges transfer aliases inside the target namespace.

## Ownership boundaries

API views handle authorization, request validation, and response formatting. They translate the viewer capability into `CardPoolScope` once and pass that visibility value into card-derived repositories, services, and payload builders. Core code does not inspect users or staff state. Card, card-group, catalog, deck, image, and export queries apply the scope before search, counts, ordering, previews, or aggregation, while unrestricted persistence helpers remain deliberate administrative/domain operations.

This separation keeps imports, staff tools, deck building, and future clients aligned on the same card behavior.
