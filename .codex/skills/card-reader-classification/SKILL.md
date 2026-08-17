---
name: card-reader-classification
description: Work on Card Reader card classification and identity across core, API, parser, and frontend. Use when changing card pools, roles, factions, mana families, classification rules or review items, import inference, card identity matching, default sorting, Gallery classification filters, or related migrations and developer-data compatibility.
---

# Card Reader Classification

Follow `AGENTS.md` first and use `card-reader-core` for shared backend changes. Classification is cross-cutting: trace core persistence, import behavior, API contracts, frontend state, migrations, and developer-data adoption before changing a field or rule.

## Classification Model

- Treat `card_pool`, `card_roles`, `card_factions`, and `card_mana_families` as independent Card-level dimensions.
- Persist exactly one valid pool. Persist zero or more code-owned roles, factions, and mana families.
- Derive Normal, No faction, and Colorless from empty assignment sets; never persist them as classification values.
- Keep roles and mana families out of Card identity. Scope human-readable identity to the exact canonical `(card_pool, card_factions)` namespace.
- Allow multi-valued and cross-pool assignments unless an explicit product workflow narrows a query.
- Treat stored Card mana families as authoritative for classification, filtering, sorting, and deck building. Treat latest-version Symbols as authoritative for printed mana evidence and calculations; symbol edits must not silently rewrite Card families.

## Atomic Invariants

- Mutate mana-family assignments through the cards classification seam so the set and `mana_family_sort_key` update atomically.
- Mutate factions through the cards identity seam so assignments, Card namespace keys, and alias namespace keys update atomically.
- Preserve Card roles, factions, and mana families when an import matches an existing stable Card; record differing inferred evidence for review instead of silently replacing stable classification.
- Keep classification review snapshots immutable per mismatching import item. Resolve or dismiss them explicitly; ordinary Card edits must not auto-close them.
- Retarget review rows during Card merges while preserving their evidence snapshots and historical pool context.

## Import And Matching Rules

- Keep the ordinary match path explicit about pool and canonical faction set.
- Use the special empty-faction Evil fallback only for untargeted Evil imports with reparse matching enabled.
- In that fallback, search historical image checksums and normalized names/aliases across factioned Evil Cards. Reuse only one unambiguous candidate; singleton evidence sets must agree.
- Refuse ambiguous or conflicting matches. A transitional no-faction Evil Card must emit `evil_faction_unresolved` evidence and link reviewers to its Card tab.
- Keep parser evidence and stable Card classification separate. Route persistence decisions through core import/card services rather than parser-local writes.

## Sorting And Gallery Policy

- Keep canonical pool-specific default sorting as mirrored declarative component lists in backend and frontend code.
- Translate query-backed sorting into SQL annotations and paginate after sorting; use client sorting only for already-loaded embedded collections.
- Sort multi-valued dimensions by earliest effective value and then complete membership vector. Use the indexed mana-family sort key for query-backed family sorting.
- Keep Gallery facet visibility and route sanitation in the cards-domain Gallery policy. Do not infer it from data, counts, or classification rules.
- Keep pool-scoped Keywords, Tags, and Types availability separate from whole-facet visibility. Failed catalog requests must not erase route state.
- Keep Admin and Review global across pools and require new imports to select both pool and template explicitly.
- Preserve equal public read access for Player, Evil, and Neutral card data; do not add viewer capability fields or pool-dependent redaction.

## Workflow And Checks

1. Identify every authority affected: stored Card classification, latest-version evidence, identity, sorting, filtering, import inference, and serialized compatibility.
2. Inspect the cards repositories/services, import classification service, API serializers/views, frontend cards domain, and affected migrations.
3. Define compatibility for existing rows and retained developer-data versions before changing required fields or code-owned values.
4. Add regression coverage for atomic updates, ambiguous matching, public/all-pool behavior, SQL ordering, route sanitation, and compatibility as applicable.
5. Update classification docs and the database diagram when contracts or schema change.
6. Run core, API, parser, frontend, and integration checks in proportion to the touched surfaces.

## Hotspots

- `services/core/src/card_reader_core/repositories/cards`
- `services/core/src/card_reader_core/services/cards`
- `services/core/src/card_reader_core/services/imports/classification.py`
- `services/core/src/card_reader_core/services/classification_rules`
- `services/core/src/card_reader_core/services/classification_reviews`
- `services/parser/src`
- `services/api/src/card_reader_api`
- `frontend/src/domain/cards`
- `frontend/src/features/review-queue`
- `dev-data/selection.json`
- `docs/card-classification-*.md`
