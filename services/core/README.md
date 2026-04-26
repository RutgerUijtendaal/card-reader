# Card Reader Core

`services/core` contains the shared backend foundation used by the API, parser, and integration
tests.

## Responsibilities

- Django domain models and migrations
- Database connection and schema adoption helpers
- Repositories and business services
- Storage path resolution
- Template loading interfaces
- Shared Django settings for non-HTTP processes

## Django Settings

`card_reader_core.django_settings` is the neutral Django settings module used by background and
non-HTTP processes. The parser uses this settings module so it can access Django models and services
without importing API views, serializers, URLs, or DRF configuration.

The API extends the core settings in `card_reader_api.project.settings`.

## Data Ownership

Django owns the domain schema through migrations in this package. Existing databases are verified and
adopted through the schema adoption flow. New databases are created through Django migrations.

SQLite is the default database.

## Commands

```bash
pnpm --filter @card-reader/core lint
pnpm --filter @card-reader/core typecheck
```
