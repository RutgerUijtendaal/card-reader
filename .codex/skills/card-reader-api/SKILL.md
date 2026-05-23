---
name: card-reader-api
description: Work on the Card Reader Django and DRF API service. Use when adding or updating endpoints, serializers, views, auth behavior, seeds, management commands, API settings, or API-side business flow in this repository.
---

# Card Reader API

Follow `AGENTS.md` first. Use this skill both when implementing API changes and when reviewing them. It should keep service boundaries clear and help decide whether behavior belongs in `api` or `core`.

## Core Rules

- Keep `services/api` dependent on `services/core` only.
- Do not import parser modules into the API service.
- Keep Django-owned schema changes in `services/core` migrations.
- Preserve the current session-auth and CSRF model unless the task explicitly requires a contract change.
- Keep API compatibility stable unless the requested work requires a deliberate change.

## Implementation Workflow

1. Inspect the existing endpoint, serializer, repository, and settings patterns before editing.
2. Decide whether the change is transport-layer behavior or domain behavior before writing code.
3. Put shared domain logic in `services/core` when it is not API-specific.
4. Keep API-specific request validation, serialization, auth checks, and response orchestration in `services/api`.
5. If schema changes are required, implement them through core models and migrations rather than API-local workarounds.
6. If the change affects auth or public/staff/superuser access, trace the current rules before changing endpoint behavior.
7. Run lint, typecheck, and relevant tests before finishing.

## Review Focus

- Parser imports or parser-coupled assumptions in API code
- Domain logic embedded in views/serializers that should live in `services/core`
- Schema changes implied in API code without matching core ownership
- Contract drift in request/response shape without an explicit reason
- Auth regressions around public, staff-only, or superuser-only behavior
- Missing tests for endpoint behavior or permission boundaries

## File Hotspots

- `services/api/src/card_reader_api`
- `services/core/src/card_reader_core/models`
- `services/core/src/card_reader_core/repositories`
- `services/core/src/card_reader_core/services`

## Avoid

- Parser imports from API code
- API-local schema ownership
- Quick fixes that bypass repositories or shared services when the domain layer should own the behavior
- Mixing transport concerns and domain behavior in the same patch without a clear boundary
