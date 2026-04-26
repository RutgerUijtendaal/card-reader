# Card Reader API

Django REST API service for imports, card search, management endpoints, auth, and CSV export.

## Database

Schema is managed by Django migrations in `card_reader_core`.

Run migrations:

```bash
uv run --project . python manage.py migrate_card_reader
```

Adopt an existing pre-Django database:

```bash
uv run --project . python manage.py adopt_schema
```

Run the API locally:

```bash
uv run --project . python manage.py runserver 127.0.0.1:8000
```
