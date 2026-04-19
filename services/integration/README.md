# Card Reader Integration Tests

Cross-package test suite that exercises parser + core data layer + API migrations/seeds.

## Commands

From repo root:

- `pnpm --filter @card-reader/integration test`

## Test Scope

- Full-flow integration tests only: real OCR + real symbol detection + real DB writes.
- Fixture cases assert exact final DB state, including:
  - card identity fields
  - all parsed latest-version properties
  - all attached metadata (`symbols`, `types`, `tags`, `keywords`)
  - import job/item status fields
