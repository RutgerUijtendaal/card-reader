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

```powershell
$svg = Get-Content docs/card-database-diagram.svg -Raw; [xml]$svg | Out-Null
```

## Diagram Layout

Use the established linear schematic:

- Top band: import/parser lineage and external auth/template context.
- Left band: things built from `Card`, such as decks, sideboards, groups, aliases, and merge redirects.
- Center band: `Card` as the stable identity.
- Right band: what cards are made from, centered around `CardVersion`, images, parse results, parse flags, metadata link tables, and canonical metadata tables.

Keep `Card` visually central. Decks and groups should point to `Card`, not to `CardVersion` metadata. Avoid adding a deck-to-version-metadata callout; explain that relationship in prose if needed.

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

- Use exact model names in boxes, including long names such as `CardVersionMetadataSuggestion`; reduce label font size instead of abbreviating when needed.
- Prefer straight, aligned pairs for metadata rows:
  - `CardVersionType -> Type`
  - `CardVersionSymbol -> Symbol`
  - `CardVersionKeyword -> Keyword`
  - `CardVersionTag -> Tag`
  - `CardVersionMetadataSuggestion -> MetadataSuggestion`
- Route metadata relationships from the bottom-center of `CardVersion`, then branch horizontally into the metadata link rows.
- Put `CardVersionParseFlag` and `CardVersionParseFlagItem` above `CardVersionImage` and `ParseResult`; place the item box to the right of the parent flag.
- Draw `ImportJob.template -> Template` as a solid FK relationship, not a dashed logical key reference.
- Keep labels away from arrow crossings. If labels overlap, move the label before moving model boxes.
- Route long top-band arrows through open space. The `ImportJob.template -> Template` arrow should arc upward rather than pass through other boxes.
- Keep all boxes inside their container bands. If a box no longer fits, widen the band/canvas before accepting overflow.

## Documentation

When changing the diagram, also update nearby explanatory docs if present. For a docs-only SVG change, full project lint/typecheck is usually not useful; still validate the SVG XML and state that source checks were skipped because no executable code changed.
