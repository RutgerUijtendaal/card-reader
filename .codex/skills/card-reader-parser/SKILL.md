---
name: card-reader-parser
description: Work on the Card Reader parser and OCR pipeline. Use when changing parser polling, claim/process flow, OCR adapters, extraction logic, symbol detection, or parser-side persistence in this repository.
---

# Card Reader Parser

Follow `AGENTS.md` first. Use this skill both when implementing parser changes and when reviewing them. It should help preserve the import pipeline, keep OCR concerns isolated, and route persistence through shared domain layers.

## Core Rules

- Keep `services/parser` dependent on `services/core` only.
- Do not import API views, serializers, routing, DRF settings, or API-only services.
- Keep parser provider-agnostic; PaddleOCR remains an adapter behind parser-owned boundaries.
- Persist results through core repositories and services instead of parser-local data shortcuts.
- Preserve the async import flow: API creates work, parser claims queued work, parser writes results back through core.

## Implementation Workflow

1. Inspect the current pipeline stage before editing.
2. Identify whether the change belongs in polling/claiming, OCR adaptation, extraction, symbol detection, or persistence before moving code.
3. Keep OCR/vendor-specific behavior isolated behind parser adapter boundaries.
4. Put shared persistence or domain behavior in `services/core` when appropriate, using feature packages under `card_reader_core.repositories` and `card_reader_core.services`.
5. Preserve idempotence and claim/process flow behavior when changing parser execution.
6. Treat data writes as domain operations; route them through existing repositories/services unless the task explicitly requires a new shared abstraction.
7. Run lint, typecheck, and relevant tests before finishing.

## Review Focus

- API-layer imports or DRF assumptions inside parser code
- OCR/vendor details leaking into unrelated parser stages
- Claim/process flow regressions, especially around idempotence or repeated work
- Persistence shortcuts that bypass shared repositories/services
- Coupling parser behavior to one OCR implementation in places that should remain adapter-based
- Missing tests around parsing flow, extraction behavior, or persistence boundaries

## File Hotspots

- `services/parser/src`
- `services/core/src/card_reader_core/repositories/import_jobs`
- `services/core/src/card_reader_core/repositories/cards`
- `services/core/src/card_reader_core/repositories/metadata`
- `services/core/src/card_reader_core/services/parser_jobs`
- `services/core/src/card_reader_core/django_settings.py`

## Avoid

- API-layer imports in parser code
- Tight coupling between parsing logic and a single OCR implementation
- Writing domain data outside shared repositories/services
- Local pipeline fixes that quietly change job-claiming semantics
- Importing from legacy `*_repository.py` paths or adding core root one-off modules
