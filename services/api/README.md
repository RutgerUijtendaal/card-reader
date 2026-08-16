# Card Reader API

`services/api` is the Django + Django REST Framework HTTP service.

## Responsibilities

- REST API compatibility for the Vue app
- Session login/logout/current-user endpoints
- Authenticated developer-data discovery, grants, protected downloads, and staff build management
- Staff-protected import, review, settings, catalog, template, CSV export, and gallery/content-version TTS export
  endpoints
- Public visibility-aware deck and sideboard TTS exports using the shared persistent-sheet payload
- Superuser-protected maintenance endpoints
- Docker API entrypoint and health endpoint
- Startup orchestration for migrations and seed commands

Domain models, migrations, repositories, and shared business services live in `services/core`.

## Commands

Run migrations:

```bash
uv run --project . python manage.py migrate_card_reader
```

Adopt and verify an existing database:

```bash
uv run --project . python manage.py adopt_schema
```

Seed configured users:

```bash
uv run --project . python manage.py seed_users
```

Run the API locally:

```bash
uv run --project . python manage.py runserver 127.0.0.1:8000
```

Run the package scripts:

```bash
pnpm --filter @card-reader/api dev
pnpm --filter @card-reader/api test
pnpm --filter @card-reader/api lint
pnpm --filter @card-reader/api typecheck
pnpm --filter @card-reader/api dev-data:doctor
```

## Auth

Auth is always enabled.

- Player-scoped `/cards`, `/cards/filters`, and direct card image endpoints are public. Evil and
  Neutral collections return `403` to non-staff callers, while restricted direct objects and assets
  return `404`. Pool-partitioned TTS sheet images remain public derived artifacts.
- The temporary `/tts/cache-test/card-image` diagnostic, symbol assets, `/health`, and `/auth/*`
  are public.
- Public deck detail and deck TTS export are available to any viewer who can access the deck.
- Import jobs, review, administrative settings APIs, catalog, templates, CSV exports, and
  `POST /exports/tts/cards` require `is_staff=true`.
- Maintenance endpoints require `is_superuser=true`.
- Developer-data metadata, browser downloads, and code creation require an active staff user or an
  active user assigned the Developer role through the managed-users API.
- Developer-data build creation, history, and lock-file downloads require `is_staff=true`.
- Bootstrap-code exchange is public by design; codes are single-use, expire after 10 minutes, and
  yield a hashed bearer token that can retry the pinned download for 30 minutes.

The Vue app uses Django session auth with CSRF protection. `/auth/me` and `/auth/login` return the
current user payload and a CSRF token used by the browser client for unsafe requests.

## Seeds

Catalog seed fixtures used by the integration suite live in
`../integration/tests/fixtures/catalog`:

- `seed-keywords.json`
- `seed-symbols.json`
- `seed-tags.json`
- `seed-templates.json`
- `seed-types.json`

The example users file instead lives at
`src/card_reader_api/seeds/seed-users.example.json`. Private local users live at
`src/card_reader_api/seeds/seed-users.local.json`; that local file is gitignored and read by
`python manage.py seed_users`.

Re-running `seed_users` updates existing configured users, including their password and staff flags.

User seed format:

```json
{
  "users": [
    {
      "username": "admin",
      "password": "change-me",
      "is_staff": true,
      "is_superuser": true
    }
  ]
}
```

## Developer data

The API owns authenticated bundle discovery, bootstrap grants, protected downloads, staff build
management, and the worker management commands. See [Developer data](../../docs/developer-data.md)
for the feature lifecycle, access model, onboarding flow, and publishing behavior.

HTTP surface:

- `GET /developer-data/current`
- `GET/POST /developer-data/builds`
- `GET /developer-data/builds/{build_id}/lock`
- `POST /developer-data/grants`
- `POST /developer-data/grants/exchange`
- `GET /developer-data/bundles/{version}/download`

## Docker

The API container runs:

```bash
python manage.py migrate_card_reader
python manage.py seed_users
gunicorn card_reader_api.project.wsgi:application --pythonpath src --bind 0.0.0.0:8000
```

The parser and developer-data builder containers wait for the API health check and share the same
data volume. The builder processes queued staff requests; it does not import bundles into production.
