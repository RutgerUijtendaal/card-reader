# Card Reader API

`services/api` is the Django + Django REST Framework HTTP service.

## Responsibilities

- REST API compatibility for the Vue app
- Session login/logout/current-user endpoints
- Staff-protected import, review, settings, catalog, template, and export endpoints
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

Seed configured users and default catalog/template data:

```bash
uv run --project . python manage.py seed_users
uv run --project . python manage.py seed_defaults
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
```

## Auth

Auth is enabled by default with `CARD_READER_AUTH_ENABLED=true`.

- `/cards`, `/cards/filters`, card image endpoints, symbol assets, `/health`, and `/auth/*` are public.
- Import jobs, review, settings, catalog, templates, and exports require `is_staff=true`.
- Maintenance endpoints require `is_superuser=true`.

The Vue app uses Django session auth with CSRF protection. `/auth/me` and `/auth/login` return the
current user payload and a CSRF token used by the browser client for unsafe requests.

## Seeds

Default seed JSON files live in `src/card_reader_api/seeds`:

- `seed-keywords.json`
- `seed-symbols.json`
- `seed-templates.json`
- `seed-users.example.json`

Private local users live in `src/card_reader_api/seeds/seed-users.local.json`. The local users file is
gitignored and read by `python manage.py seed_users`.

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

## Docker

The API container runs:

```bash
python manage.py migrate_card_reader
python manage.py seed_users
python manage.py seed_defaults
gunicorn card_reader_api.project.wsgi:application --pythonpath src --bind 0.0.0.0:8000
```

The parser container waits for the API health check and shares the same data volume.
