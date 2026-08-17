---
name: card-reader-api
description: Work on the Card Reader Django and DRF API service. Use when adding or updating endpoints, serializers, views, auth behavior, seeds, management commands, API settings, or API-side business flow in this repository.
---

# Card Reader API

Follow `AGENTS.md` first. Use this skill both when implementing API changes and when reviewing them. Use `card-reader-core` for shared domain behavior and add the matching specialist skill for classification, developer data, notifications, or TTS changes.

## Core Rules

- Keep `services/api` dependent on `services/core` only.
- Do not import parser modules into the API service.
- Keep Django-owned schema changes in `services/core` migrations.
- Preserve the current session-auth and CSRF model unless the task explicitly requires a contract change.
- Keep API compatibility stable unless the requested work requires a deliberate change.
- Keep deck-building constraint defaults, validation, and metadata in core deck services; expose them through API views without duplicating rule definitions in serializers or frontend code.
- For idempotent creates, scope keys to the authenticated owner, return an existing result before revalidating a replayed body, and enforce race-safe uniqueness in the database as well as the service lookup path. Keep a durable used-key outcome when the created resource can be deleted, so an old retry cannot recreate an intentionally deleted resource.
- Keep Player, Evil, and Neutral card data equally public. Exact-pool reads use an explicit `card_pool`; global reads cover every pool.
- Treat workspace selection as browsing context, not authorization. Keep Admin, Review, maintenance, and other global staff operations independent of the selected workspace.
- Require every new import to provide both template and card pool explicitly; never inherit either from shell state.
- Keep direct persistent TTS sheet images public. Preserve staff-only export creation where required and deck-visibility rules for deck exports.
- Re-check active-user and Developer/staff access during developer-data credential exchange and downloads; keep bundle creation and build history staff-only.

## Implementation Workflow

1. Inspect the existing endpoint, serializer, repository, and settings patterns before editing.
2. Decide whether the change is transport-layer behavior or domain behavior before writing code.
3. Put shared domain logic in `services/core` when it is not API-specific, using the feature package under `card_reader_core.services`.
4. Keep API-specific request validation, serialization, auth checks, and response orchestration in `services/api`.
5. Put persistence logic in the matching feature package under `card_reader_core.repositories`.
6. If schema changes are required, implement them through core models and migrations rather than API-local workarounds.
7. If the change affects auth or public/staff/superuser access, trace the current rules before changing endpoint behavior.
8. If the change affects deck-building constraints, keep `GET /decks/rules` aligned with supported rule ids, defaults, allowed values, and example config.
9. If an endpoint returns cards, card-derived counts, or embedded cards, decide lifecycle and pool scope explicitly and keep list/detail/count behavior aligned.
10. Run lint, typecheck, and relevant tests before finishing.

## Review Focus

- Parser imports or parser-coupled assumptions in API code
- Domain logic embedded in views/serializers that should live in `services/core`
- Schema changes implied in API code without matching core ownership
- Contract drift in request/response shape without an explicit reason
- Auth regressions around public, staff-only, or superuser-only behavior
- Viewer-dependent pool redaction, capability fields, or workspace-scoped staff queues
- Import creation that silently inherits a pool or template
- Card-derived counts or embedded payloads whose pool or lifecycle scope differs from the endpoint contract
- Missing tests for endpoint behavior or permission boundaries
- Idempotency keys that are globally scoped, exposed in public payloads, checked only before a race-prone insert, or unable to distinguish first-create and replay responses
- Deck-building rule drift between core validation, API metadata, and frontend fallback assumptions

## File Hotspots

- `services/api/src/card_reader_api`
- `services/core/src/card_reader_core/models`
- `services/core/src/card_reader_core/repositories/<feature>`
- `services/core/src/card_reader_core/services/<feature>`
- `services/core/src/card_reader_core/config`
- `services/core/src/card_reader_core/storage`

## Avoid

- Parser imports from API code
- API-local schema ownership
- Quick fixes that bypass repositories or shared services when the domain layer should own the behavior
- Mixing transport concerns and domain behavior in the same patch without a clear boundary
- Adding new one-off modules in `card_reader_core` root or recreating legacy `*_repository.py` files
