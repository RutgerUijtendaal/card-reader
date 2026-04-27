FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_LINK_MODE=copy \
    DJANGO_SETTINGS_MODULE=card_reader_core.django_settings \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    FLAGS_use_mkldnn=0

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache dependency resolution separately from source changes.
COPY pyproject.toml uv.lock ./
COPY services/core/pyproject.toml services/core/README.md ./services/core/
COPY services/parser/pyproject.toml services/parser/README.md ./services/parser/

RUN uv sync --frozen --package card-reader-parser --no-dev --no-install-workspace

COPY services/core/src ./services/core/src
COPY services/parser/src ./services/parser/src

RUN uv sync --frozen --package card-reader-parser --no-dev

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_LINK_MODE=copy \
    DJANGO_SETTINGS_MODULE=card_reader_core.django_settings \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    FLAGS_use_mkldnn=0 \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app /app

WORKDIR /app/services/parser

CMD ["uv", "run", "--frozen", "--package", "card-reader-parser", "python", "-m", "card_reader_parser.main"]
