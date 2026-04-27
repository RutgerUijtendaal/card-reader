FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache dependency resolution separately from source changes.
COPY pyproject.toml uv.lock ./
COPY services/core/pyproject.toml services/core/README.md ./services/core/
COPY services/api/pyproject.toml services/api/README.md ./services/api/

RUN uv sync --frozen --package card-reader-api --no-dev --no-install-workspace

COPY services/core/src ./services/core/src
COPY services/api/src ./services/api/src
COPY services/api/manage.py ./services/api/manage.py

RUN uv sync --frozen --package card-reader-api --no-dev

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app /app

WORKDIR /app/services/api

EXPOSE 8000

CMD ["sh", "-c", "uv run --frozen --package card-reader-api python manage.py migrate_card_reader && uv run --frozen --package card-reader-api python manage.py seed_users && uv run --frozen --package card-reader-api python manage.py seed_defaults && uv run --frozen --package card-reader-api gunicorn card_reader_api.project.wsgi:application --pythonpath src --bind 0.0.0.0:8000"]
