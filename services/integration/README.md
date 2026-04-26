# Card Reader Integration Tests

`services/integration` contains cross-package tests for the parser, core data layer, migrations,
seeds, and API-compatible persistence behavior.

## Commands

From the repo root:

```bash
pnpm --filter @card-reader/integration test
```

## Scope

Integration tests exercise:

- Django migrations and seed setup
- Parser job processing
- Core repositories and services
- Real OCR and symbol detection fixture flows
- Final database state for cards, versions, metadata, images, import jobs, and import items

Fixture cases assert exact stored data, including:

- card identity fields
- latest-version parsed properties
- attached metadata (`symbols`, `types`, `tags`, `keywords`)
- import job and item statuses
