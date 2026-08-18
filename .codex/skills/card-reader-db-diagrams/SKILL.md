---
name: card-reader-db-diagrams
description: Maintain Card Reader database schema diagrams and SVG schematics. Use when creating, updating, reviewing, or explaining repository database diagrams, especially docs/card-database-diagram.svg or model relationship diagrams for card, import, deck, parser, metadata, or auth-related Django models.
---

# Card Reader DB Diagrams

## Core Workflow

1. Read `AGENTS.md` and the relevant Django model files in `services/core/src/card_reader_core/models`.
2. Treat model class and field names as source of truth; do not infer relationships from service behavior alone.
3. Update `docs/card-database-diagram.svg` whenever database models or relationships change in a way the diagram should represent.
4. Keep generated scratch copies under `.tmp/codex/` only while iterating; the committed source of truth is the SVG in `docs/`.
5. Validate SVG XML after editing:

```bash
uv run --no-project python -c "import xml.etree.ElementTree as ET; ET.parse('docs/card-database-diagram.svg')"
```

## Diagram Layout

Use a banded linear schematic:

- Top band: import/parser lineage and external auth/template context.
- Left band: things built from `Card`, such as decks, sideboards, groups, aliases, and merge redirects.
- Center band: `Card` as the stable identity.
- Right-center band: version and review lineage, centered around `CardVersion`, images, parse results, and parse flags.
- Far-right band: metadata link tables and their aligned canonical metadata tables.

Keep `Card` visually central. Decks and groups should point to `Card`, not to `CardVersion` metadata. Avoid adding a deck-to-version-metadata callout; explain that relationship in prose if needed. Preserve these semantic groupings while they remain useful, but split, resize, or rename bands when a group can no longer provide clear routing space.

## Current Model Semantics

- `Card` is the stable identity used by decks, groups, aliases, merge redirects, imports, and parsed versions.
- `CardVersion` is the parsed snapshot/history entry for a card.
- `ContentVersion` is the actual current model name for content release/version markers. `ImportJob.content_version` and `CardVersion.content_version` both point to it.
- `ImportJob.template` is a real FK to `Template.id` stored in the `template_id` database column. Public payloads still expose `template_id` as the template key.
- `CardVersion.template` is the real FK from parsed version to `Template`.
- `CardVersionParseFlag.submitted_by` is required and points to the Django auth user.
- `CardVersionParseFlagItem.reviewed_by` is nullable. Show it as optional/dashed or label it clearly as nullable when the distinction matters.
- `MetadataSuggestion.accepted_tag` and `MetadataSuggestion.accepted_type` are optional accepted metadata links.

## SVG Style Rules

- Use orthogonal connectors only: every relationship segment must be horizontal or vertical. Do not use curves, arcs, or diagonal segments.
- Treat the open space between boxes and bands as explicit routing lanes. A connector must travel through those lanes and must never cross an entity box, even when a more direct route would be shorter.
- Give every relationship its own final attachment segment and its own attachment point on the destination box. Relationships may share a trunk while travelling, but they must split before approaching a box; do not stack arrowheads or merge the final stretch.
- Keep visible clearance between parallel lanes, box edges, labels, and arrowheads. Prefer a longer perimeter route over a tight path through a populated group.
- Expand the canvas, band, or inter-band gutter before shrinking boxes, reducing readable text, or accepting crowded routing.
- Reserve box sides intentionally: use distinct ports for multiple incoming relationships, and prefer the side that faces the connector's owning lane.
- Use exact model names in boxes, including long names such as `CardVersionMetadataSuggestion`; reduce label font size instead of abbreviating when needed.
- Prefer straight, aligned pairs for metadata rows:
  - `CardVersionType -> Type`
  - `CardVersionSymbol -> Symbol`
  - `CardVersionKeyword -> Keyword`
  - `CardVersionTag -> Tag`
  - `CardVersionMetadataSuggestion -> MetadataSuggestion`
- Route metadata relationships from `CardVersion` into a clear collector lane, then branch horizontally into the metadata link rows. The collector is a travel trunk only; each metadata row keeps a separate final segment.
- Put `CardVersionParseFlag` and `CardVersionParseFlagItem` above `CardVersionImage` and `ParseResult`; place the item box to the right of the parent flag.
- Draw `ImportJob.template -> Template` as a solid FK relationship, not a dashed logical key reference.
- Treat a label and its background stroke as a routing obstacle. A label may mask its own connector for readability, but it must not cover an unrelated connector, entity border, arrowhead, or another label. Reserve a clear label shelf within the lane; if none exists, reroute the relationship or expand the layout.
- Route long top-band relationships through the reserved upper, lower, or perimeter lanes. In particular, route `ImportJob.template -> Template` above the boxes with orthogonal segments.
- Keep all boxes inside their container bands. If a box no longer fits, widen the band/canvas before accepting overflow.

Before finishing, inspect a rendered raster copy at a readable scale in addition to validating the XML. Check every connector end and every long lane for box intersections, merged final approaches, clipped or colliding label backgrounds, and accidental diagonal or curved segments.

## Documentation

When changing the diagram, also update nearby explanatory docs if present. For a docs-only SVG change, full project lint/typecheck is usually not useful; still validate the SVG XML and state that source checks were skipped because no executable code changed.
