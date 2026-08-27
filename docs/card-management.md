# Card Management

Card management separates a card's stable identity from the content extracted or edited at a particular point in time. That distinction lets the application retain history, repair parsing results, group related printings, and safely consolidate duplicates.

## Cards and versions

A `Card` is the durable identity referenced by decks, groups, aliases, and application URLs. A `CardVersion` contains versioned content such as parsed text, images, template selection, symbols, and metadata relations.

Each card points to its current version, while older versions remain available for history and comparison. Imports, reparses, and edits use this version model so a correction does not destroy the record of what existed previously.

Content versions provide an additional history boundary for related changes made during import and editing workflows. The UI exposes this history through card detail and generation views.

## Pool, roles, factions, and mana families

Every stable card identity belongs to exactly one of the **Player**, **Evil**, or **Neutral** pools. Neutral is currently a separate pool rather than an implicit overlay in Player or Evil views. A card can also hold any combination of the code-owned Hero, Boss, Location, Boon, Event, Shop Item, Directive, Reminder, and Mana roles, any combination of the Order, Blood, Dark, Metal, and Fire factions, and any combination of the Arcane, Dark, Divine, Martial, Occult, and Primal mana families. Directive, Reminder, and Mana identify those card kinds without assigning a mana family or Evil faction. **Normal**, **No faction**, and **Colorless** are displayed names for empty assignment sets; none is persisted as an assignment.

Role, faction, and mana-family assignment keys allow up to 64 characters. Their definitions, labels, and ordering are code-owned. Hero remains the only role with existing deck-builder or Playtester behavior; every other role and all factions are descriptive until their gameplay rules are designed.

Staff edit all four dimensions in the Card tab alongside lifecycle state and deck-building configuration. They are intentionally independent of template selection, which remains version-level parsing configuration. Role, faction, and mana-family definitions remain code-owned, while Admin Catalog exposes their current usage and staff-editable pool-specific Tag, Type, or Symbol inference rules. Normal, No faction, and Colorless appear there as read-only derived empty states. Mana-family definitions link to their existing mana Symbol for display instead of duplicating icon assets.

The migration-owned defaults map the Directive and Reminder Types to their matching roles only in the Evil pool. The migration adds those roles to active and deprecated Evil Cards whose authoritative latest version has the corresponding Type, preserving every existing role. Player and Neutral receive no default rule or backfill, and a Type found only on an older version does not qualify. Manual assignments and custom rules remain available in every pool.

Admin Catalog and Review are global staff operational surfaces. They query every card pool regardless of the Player/Evil/Neutral shell workspace. Their mixed-pool counts, queues, searches, suggestions, and previews always retain visible pool classification so duplicate names remain distinguishable. Review separates user-reported parse flags from durable classification items created when a new imported version infers different pool, role, faction, or mana-family values than its stable Card. Classification items retain their import-time evidence until staff explicitly resolve them or keep the existing classification; Card merges retarget them to the surviving Card while preserving the captured evidence and reviewed version.

Card collections accept one pool plus independent role, faction, and mana-family inclusion/exclusion filters with `any` or `all` matching. Player, Evil, and Neutral are public primary site workspaces selected from the sidenav. The public Home page at `/` introduces all three collections together, with Player and Evil as its primary paths; the saved workspace is only shown as quiet context and never changes the Home URL. The Gallery remains a separate browsing surface at `/cards`, where the active workspace supplies the pool and is serialized in shareable Gallery URLs. Player is the default, all three options are always available, and the saved workspace survives login and logout. No workspace has a default role, faction, or mana-family constraint, and Neutral is never added as an implicit overlay.

The ordinary Gallery uses a small code-owned presentation matrix. Roles are hidden in every pool and the Gallery has no default Hero exclusion; Factions appear only in Evil; Mana, including mana-cost bounds, Affinity, and Devotion appear only in Player. Types, generic symbols and stats, Keywords, and Tags remain shared. Direct links, browser history, and pool changes reset values belonging to hidden facets before the canonical route and request are built. This presentation policy does not remove backend filter capabilities or affect global Admin, Review, maintenance, card editing, imports, deck building, or Playtester. Deck-building searches continue applying their own explicit Hero inclusion or exclusion rules.

Within the shared Keyword, Tag, and Type facets, the Gallery loads only values linked to the latest version of at least one active Card in its exact Player, Evil, or Neutral pool. These values depend on the pool, not on the Gallery's other active filters or current result count. After a successful catalog load, unavailable metadata keys are removed from the canonical URL before card results, summaries, CSV, or TTS exports use them. A failed or stale catalog request never erases route state or installs another pool's values, and card browsing remains available with a filter-catalog retry. `GET /cards/filters` without `card_pool` retains the complete all-pool catalog for global Admin, Review, maintenance, and other existing consumers; Symbols and other filter families retain their previous value contracts. This path is query-backed without a server or persistent browser cache.

Staff can export the current Player, Evil, or Neutral Gallery selection to TTS. Persistent sheets are partitioned by pool so exports normally reuse atlases containing cards from the same pool. Every pool uses the same stable public sheet URL contract: an existing TTS object sees later rendered card-art updates without being re-exported. Deck TTS exports remain Player-only alongside the current deck workflow.

Switching workspaces keeps global staff and settings routes mounted, resets Gallery to the selected pool's canonical defaults, and keeps card or group resources open while updating their Gallery return context. Player-only deck and Playtester routes fall back to the selected non-Player Gallery only when they cannot remain active. Every new import starts without a template or pool selection and requires both choices explicitly; role, faction, and mana-family inference default independently to Automatic using an immutable snapshot of matching Tag, Type, and Symbol rules.

After the one-time pre-classification migration adoption described in the import guide, inference rules affect future jobs only. Editing, disabling, or repointing a rule does not reclassify existing cards or reinterpret queued jobs. Tag, Type, and Symbol detail views show reverse rule references, and referenced sources are protected from deletion until their rules are removed or repointed.

Import classification initializes only new card identities. Untargeted imports with known factions match latest image hashes, primary names, and aliases inside the selected pool and exact canonical faction set; mana families never participate in that identity namespace. An empty Evil faction result instead means unknown: after ordinary empty-namespace matching, Core searches factioned Evil Cards by every historical image checksum and by normalized primary names and aliases. It reuses a Card only when neither source is ambiguous and both sources agree when present. Existing cards and targeted reparses keep their authoritative Card-tab pool, roles, factions, and mana families; differing inference completes successfully, preserves the stored classification, and creates a durable Review item with both snapshots and rule evidence instead of silently reclassifying the Card. Ambiguous, conflicting, or unmatched Evil results stay independent as transitional no-faction Cards with an actionable `evil_faction_unresolved` warning. Targeted reparses, other pools, known-faction imports, and disabled reparse matching remain namespace-scoped.

## Metadata and aliases

Card versions connect parsed content to managed catalogs such as card types, keywords, tags, symbols, and metadata groups. These relationships power filtering, display, rules text, and deck-building behavior.

Aliases provide alternate names or identifiers for the same card identity. Primary and alias keys share a namespace scoped by pool plus the card's exact canonical faction set. The same normalized key may exist independently in another pool or faction namespace. Rename, pool, and faction edits validate the complete destination namespace and move the primary name, every alias, and faction assignments atomically. One durable lock row per pool serializes primary and alias mutations across imports, edits, merges, and developer-data adoption.

### Mana families

The application owns six canonical, multi-valued Card mana families in a fixed release-time order: Arcane, Dark, Divine, Martial, Occult, and Primal. Empty assignments are displayed as Colorless. Each definition links to its existing mana Symbol for display, while paired mana and affinity Symbols seed Player inference rules. The legacy `primla-affinity` Symbol is recognized as Primal when present.

`Card.mana_family_sort_key` stores an indexed rank derived atomically from the complete assignment set. Family sets sort by their earliest canonical family and then their complete membership vector, so multicolor Cards remain beside the matching earliest family; Colorless uses the final no-family bucket. Filtering, sorting, and deck-building decisions read the Card assignments. Editing or reparsing version Symbols never mutates those authoritative assignments.

Card gallery APIs expose `sort=mana_type_asc` and filters through repeated `mana_family_keys` and `mana_family_exclude_keys` parameters plus `mana_family_match=any|all`. Those parameters now query stored Card assignments while retaining their public names for compatibility. `GET /cards/filters` supplies the ordered classification catalog and linked display Symbols used by Gallery filters and hero-derived deck presets.

Version Symbols remain authoritative for printed mana cost, mana value, mana distribution, Affinity and Devotion, exact raw-Symbol filters, parser output, and diagnostic evidence. This keeps what a card *is classified as* separate from what a particular printing *shows*.

`sort=default` is the default for single-pool card collections. Player orders by canonical mana family, then Hero, the default role order, and ascending mana value. Evil orders by Order, Blood, Dark, Metal, Fire, then no faction, followed by Boss, Location, the default role order, and ascending mana value. Neutral uses the default role order directly. That shared order is Normal, Hero, Boss, Location, Boon, Event, Shop Item, Directive, Reminder, then Mana; a pool-specific priority moves the named roles ahead without duplicating them. Multi-valued classifications use their earliest effective value and complete effective membership as tie-breakers; null mana values sort last, and names, labels, and Card ids make every order deterministic. Grouped Gallery results use the anchor Card's classifications and latest-version metadata.

The backend and frontend express these priorities as mirrored declarative component lists. Query-backed collections translate the components to SQL annotations over indexed Card classification and version fields and paginate after database ordering. The default path does not load the Type catalog or materialize the complete result set, keeping future priority changes localized without sacrificing pagination performance.

Card sort preferences use one versioned browser-origin `localStorage` record. The first load after this change replaces the legacy global default and per-surface overrides with `default` and empty overrides, after which users can customize them again. This migration runs independently in each browser profile when it next opens the app; server-side or Django migrations cannot rewrite remote browser storage.

## Lifecycle state

Cards have an explicit lifecycle state:

- Active cards appear by default in gallery, public group views, catalog previews, exports, deck building, and Playtester selection.
- Deprecated cards remain directly retrievable and available in explicit management queries, but are hidden from ordinary browsing and selection.

Deprecating or reclassifying a card does not silently remove it from existing decks or groups. Those relationships remain visible so owners can resolve them deliberately. Deck validation and management views surface the resulting warnings or invalid state, and embedded deck payloads always expose the referenced card's real identity, pool, and content.

## Card groups

Groups collect related card identities, such as alternate printings or variants, in an intentional order. Every group has an active anchor card that acts as its primary public identity.

Groups may intentionally span pools. Public payloads include every active member across all three pools; staff permissions are required only to manage the group. Linked members retain their own pool classification, show a pool badge when it differs from the active workspace, and preserve the originating workspace for return navigation. The group route uses the anchor's pool rather than borrowing the source card's pool.

Deprecated non-anchor members may remain attached for administrative history but are omitted from active public group views. Changing group membership or order is handled through the group service so anchor and lifecycle invariants remain consistent.

## Merging duplicates

Merging consolidates duplicate card identities while preserving useful history. The merge workflow moves compatible versions, aliases, metadata relationships, group membership, and other references to the surviving card. Old identifiers can redirect to the survivor instead of becoming broken links.

Merges are domain operations, not raw row deletion. Conflict checks and a preview step allow staff to understand the result before committing a merge. Cross-pool and cross-faction-namespace merges are rejected; staff must explicitly reclassify a source first when that is intentional. Mana-family differences are non-blocking preview warnings, and the explicitly selected target Card's assignments survive unchanged. Same-namespace merges transfer aliases inside the target namespace.

## Ownership boundaries

API views handle endpoint authorization, request validation, and response formatting. Card-derived repositories, services, and payload builders do not receive viewer-dependent pool entitlements: global reads cover all pools, pool-specific reads use an exact requested pool, and genuine Player-only workflows use an explicit Player predicate. Core code does not inspect users or staff state.

This separation keeps imports, staff tools, deck building, and future clients aligned on the same card behavior.
