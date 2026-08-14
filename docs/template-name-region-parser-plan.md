# Template Parser: Name-Only Region

Status: implemented.

## Goal

Add `name` as a supported template-region parser type for card layouts where the name occupies a crop that contains no mana cost. The parser reads that crop with the configured OCR settings and contributes only the normalized card name. It must not load mana symbol candidates, call symbol detection, infer variable or numeric mana, emit detected symbols, or write mana fields.

Existing `name_mana_cost` templates and behavior remain valid. Templates choose the parser that matches their artwork; this plan does not rewrite existing template definitions.

## Locked behavior

- `name` and `name_mana_cost` are separate supported parser types.
- `name` returns OCR text, OCR lines, confidence, debug evidence, and `normalized_fields.name` only.
- The name-only parser never depends on `SymbolDetector` and receives no symbol catalog.
- The aggregate parsed-card contract continues supplying empty `mana_cost`, `mana_symbols`, and `mana_total` defaults when no region produces them. Those defaults are assembly behavior, not mana work performed by `name`.
- Empty usable OCR falls back to the image stem, matching the current card-name fallback contract.
- Shared non-mana cleanup, including removal of the decorative star tail already handled by the combined parser, applies to both name parsers.
- Mana-specific cleanup remains exclusive to `name_mana_cost`. In particular, `name` must preserve a legitimate numeric suffix such as `Prototype 2` because it has no mana evidence that would justify stripping it.
- A template may define at most one name-producing region across `name` and `name_mana_cost`. Core validation rejects duplicate `name` regions and mixed `name` plus `name_mana_cost` definitions instead of relying on region order to decide which value wins.
- Templates without a name-producing region remain valid for backward compatibility and continue using the final image-stem fallback.
- `name` is unrelated to symbol `detector_type`; the latter remains the separate catalog contract.

## Implementation

### Backend parser-type registry

Create one core-owned Python registry for template parser-type keys and canonical order. Core template validation and parser dispatch both consume it through the public `card_reader_core.services.templates` API. This removes the current duplicated Python literals without trying to share runtime code with TypeScript.

The ordered supported values become:

1. `name`
2. `name_mana_cost`
3. `type_tag`
4. `rules_text`
5. `attack`
6. `health`
7. `affinity`

Keep parser dispatch explicit because handlers have intentionally different inputs. Consolidating the keys must not force the heterogeneous region handlers into an artificial generic interface.

Extend `TemplateService` validation to accept `name` and enforce the single name-producing-region rule. Validation errors identify the conflicting region indices/ids and the two mutually exclusive parser types. No Django model or database migration is required because template definitions already store parser types inside JSON.

### OCR/name extraction seam

Add a `NameParser` under the parser-owned region package. It receives `OcrRunner`, resolves the region's existing `ocr_config`, runs OCR, normalizes the lines/text, performs only shared name cleanup, and returns a `RegionParseResult` with:

- the configured `region_name`;
- raw joined OCR `text` and filtered `lines`;
- average OCR confidence;
- an empty `detected_symbols` collection;
- exactly one normalized field, `name`;
- debug evidence for the OCR configuration and raw/filtered line counts, with no symbol-candidate or mana evidence.

Extract the small provider-neutral OCR text preparation and shared name cleanup currently embedded in `NameManaCostParser` into parser-owned helpers used by both parsers. Preserve `name_mana_cost` output and heuristics byte-for-byte where practical: mana candidate selection, symbol detection, X handling, totals, mana fields, logging, and mana-dependent numeric cleanup remain in that parser.

Do not implement `NameParser` as a mode flag on `NameManaCostParser`; its constructor and call contract should make the absence of mana work structurally clear.

### Card parser dispatch and confidence

Instantiate and dispatch `NameParser` for `parser_type == "name"`. Do not pass the symbol list to it.

Update confidence assembly so:

- the `name` confidence comes from whichever permitted name-producing parser is present;
- `mana_cost` confidence comes only from `name_mana_cost` and is `0.0` for a name-only template;
- overall confidence counts the name once and does not invent a mana confidence contribution for name-only cards.

Raw OCR continues recording the region under its configured `region_id`, including `parser_type` inside the snapshotted template definition. Parsed symbol ids remain unaffected by name-only regions.

### Frontend template contract

Keep a separate frontend definition, but consolidate it within the templates domain:

- define one ordered typed `TEMPLATE_PARSER_TYPE_DEFINITIONS` registry containing the seven keys and labels;
- derive `TemplateParserType` from that registry rather than maintaining a second frontend union;
- build the Template Admin supported-types hint from the registry;
- add an explicit preview-overlay treatment for `name` and keep the mapping exhaustive so a later parser type cannot silently inherit the Affinity fallback color.

Keep the default Admin template example on `name_mana_cost`, because its demonstrated top bar contains both concerns. Administrators can select `name` by editing a suitable template's region JSON. This plan does not add a graphical region-builder control.

### API, imports, and developer data

Template create/update and import-job snapshots already carry validated template definition JSON. Audit these paths and extend tests where a closed parser-type union exists; do not add a new API field or developer-data format version.

New jobs snapshot the chosen template definition as usual. Existing jobs and templates containing `name_mana_cost` remain deterministic and require no migration. Developer-data export/import must round-trip a template containing `name` without rewriting its parser type.

## Public contract change

`TemplateRegionDefinition.parser_type` accepts:

```text
name | name_mana_cost | type_tag | rules_text | attack | health | affinity
```

For a `name` region, its `RegionParseResult.normalized_fields` contains only `name`. The final `ParsedCard.normalized_fields` retains the existing stable field set, with empty mana defaults when no mana-producing region exists.

## Validation plan

### Core and API

- `TemplateService` accepts a valid `name` region.
- Existing six parser types remain accepted and unknown values remain rejected.
- Duplicate `name`, duplicate `name_mana_cost`, and mixed name-producing regions are rejected clearly.
- Existing persisted template definitions load unchanged.
- Template create/update API tests cover `name` without changing the response shape.
- Developer-data template round trips preserve `name` and the current bundle format.

### Parser

- `NameParser` extracts a normal OCR name and reports confidence/lines/debug evidence.
- Empty OCR falls back to the image stem.
- Decorative star-tail cleanup matches the combined parser.
- Numeric suffixes are preserved by `name`.
- The symbol detector is never constructed or called through the name-only path, and the result has no detected symbols.
- The result contains no mana normalized fields.
- Card-level dispatch fills the card name and leaves aggregate mana fields empty.
- Name confidence uses the name-only region, mana confidence stays zero, and overall confidence counts the name once.
- Existing `NameManaCostParser` and full `CardParser` tests remain unchanged and green.

### Frontend

- The typed registry contains all seven values in canonical order.
- `TemplateParserType` accepts `name` and rejects unsupported literals at typecheck time.
- Template Admin displays the generated supported-types hint including `name`.
- Template preview renders a `name` region with its explicit overlay style.
- Existing template preview and JSON editing behavior remains unchanged.

## Documentation

[Imports and parsing](imports-and-parsing.md) records the supported region parser types and when to choose `name` versus `name_mana_cost`. Existing seed and persisted template contracts remain compatible because `name_mana_cost` is unchanged, templates without a name-producing region remain valid, and the parser type is stored in existing definition JSON. No database diagram update or migration was required.

## Execution sequence

1. Inventory persisted and seed/developer-data templates to confirm no template currently has multiple name-producing regions.
2. Add the core Python parser-type registry and consume it from template validation and parser dispatch.
3. Add the single-name-source validation and focused core/API tests.
4. Extract the shared OCR/name text helpers without changing existing combined-parser behavior.
5. Implement `NameParser`, card dispatch, and corrected confidence semantics with parser tests.
6. Add the frontend typed registry, Admin hint, overlay handling, and frontend tests.
7. Verify template snapshot and developer-data round trips, then update current-state parsing docs.
8. Run permitted core, API, parser, and web lint/typecheck and targeted tests. Do not run the prohibited local integration suite.
9. Open a focused non-draft PR and nurture CI and automatic Codex review until clean.

## Acceptance criteria

- A validated template can use `parser_type: "name"`.
- Parsing that region fills the card name without symbol detection or mana parsing.
- Name-only cards retain empty aggregate mana fields and correct name/overall confidence.
- Existing `name_mana_cost` templates and results do not change.
- Ambiguous multiple name-producing regions are rejected before parsing.
- Python parser-type keys have one core-owned registry; frontend keys have one templates-domain registry.
- Template Admin, API, import snapshots, and developer-data accept and preserve the new value.
- Documentation, lint, typecheck, targeted tests, CI, and automatic review are clean.

## Non-goals

- Adding a mana-only parser type.
- Auto-detecting whether a name crop also contains mana.
- Rewriting existing templates from `name_mana_cost` to `name`.
- Changing card identity, classification inference, OCR providers, symbol detector types, or import override behavior.
- Replacing the JSON template editor with a graphical region designer.
- Serving parser-type metadata dynamically from the backend to the frontend.
