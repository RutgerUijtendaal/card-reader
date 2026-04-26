FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only dependency manifests first to maximize cache hits.
COPY services/core/pyproject.toml services/core/uv.lock services/core/README.md ./services/core/
COPY services/api/pyproject.toml services/api/uv.lock services/api/README.md ./services/api/

# Copy source after manifests.
COPY services/core/src ./services/core/src
COPY services/api/src ./services/api/src
COPY services/api/manage.py ./services/api/manage.py

WORKDIR /app/services/api
RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["sh", "-c", "uv run --no-dev python manage.py migrate_card_reader && uv run --no-dev python manage.py seed_defaults && uv run --no-dev gunicorn card_reader_api.project.wsgi:application --pythonpath src --bind 0.0.0.0:8000"]
