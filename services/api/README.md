# Card Reader API

FastAPI service for imports, card search, corrections, and CSV export.

## Database

Schema is managed with Alembic migrations.

Run migrations:

```bash
uv run --project . alembic upgrade head
```

Create a new migration revision:

```bash
uv run --project . alembic revision -m "describe change"
```
