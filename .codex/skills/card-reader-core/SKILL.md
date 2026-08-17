---
name: card-reader-core
description: Work on Card Reader's shared Python/Django domain foundation. Use when changing services/core models, migrations, repositories, domain services, configuration, database helpers, storage, shared operations, or behavior consumed by both the API and parser.
---

# Card Reader Core

Follow `AGENTS.md` first. Use this skill for shared backend behavior; combine it with a feature skill such as `card-reader-classification`, `card-reader-notifications`, `card-reader-developer-data`, or `card-reader-tts` when the change belongs to one of those domains.

## Ownership Rules

- Keep `core` independent of API views, serializers, URLs, DRF settings, and parser implementations.
- Keep the package root limited to package and Django entrypoints. Put runtime helpers in an owned package such as `config`, `storage`, `metadata`, `rules`, or `operations`.
- Put feature workflows in `services/<feature>` and persistence in `repositories/<feature>`.
- Let repositories own Django queries and writes. Let services coordinate domain rules and transactions. Keep transport shaping outside core.
- Expose stable feature APIs from package `__init__.py` files and prefer those public imports across package boundaries.
- Extend an existing feature package or shared helper when it owns the responsibility; do not recreate root-level one-off modules or legacy `*_repository.py` files.
- Preserve SQLite compatibility unless a different database is explicitly approved.

## Stateful Changes

- Define the authoritative success condition, idempotency boundary, independent failure domains, and cleanup semantics before changing a stateful workflow.
- Keep related denormalized or namespace fields inside one atomic domain seam. Do not expose a lower-level write path that can leave an invariant half-updated.
- Use database constraints for race-safe invariants in addition to service-level checks where concurrency can create duplicates.
- Dispatch notifications or external follow-up work after the authoritative transaction commits. Cleanup or fanout failure must not reverse confirmed domain success.
- Preserve compatibility for retained immutable data formats and migration histories; make adoption explicit rather than weakening the current schema.

## Implementation Workflow

1. Read the model, public service API, repository package, migrations, and tests for the affected feature.
2. Decide whether each behavior is domain orchestration, persistence, neutral runtime support, or transport behavior before editing.
3. Reuse the owning package and keep the service/repository boundary explicit.
4. Add a Django migration for schema or persisted-default changes. Keep migration data logic self-contained and safe against historical states.
5. Update `docs/card-database-diagram.svg` when card-related models or relationships change, using `card-reader-db-diagrams`.
6. Update relevant docs when behavior, permissions, contracts, onboarding, or operations change.
7. Test the public seam and important failure or replay behavior, not only internal helpers.
8. Run core lint and typecheck plus the narrowest relevant service and integration tests.

## Checks

From the repository root, prefer targeted commands while iterating:

```text
pnpm --filter @card-reader/core lint
pnpm --filter @card-reader/core typecheck
pnpm --filter @card-reader/core test
```

Also run API, parser, or integration checks when their contracts or workflows consume the changed core behavior.

## Review Focus

- API or parser details leaking into core
- Django query/write behavior hidden in services
- Domain decisions embedded in repositories
- Deep imports that bypass a feature's public API
- Partial writes that can violate cached keys, membership sets, aliases, or other coupled invariants
- Migrations that depend on current runtime code or assume data introduced by a later migration
- Post-commit work that can block or undo authoritative success
- Missing diagram, docs, or cross-service coverage for a shared contract change
