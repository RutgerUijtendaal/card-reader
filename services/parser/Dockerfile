FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

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

# Copy only dependency manifests first to maximize cache hits.
COPY services/core/pyproject.toml services/core/uv.lock services/core/README.md ./services/core/
COPY services/parser/pyproject.toml services/parser/uv.lock services/parser/README.md ./services/parser/
COPY services/api/pyproject.toml services/parser/uv.lock services/parser/README.md ./services/api/

# Copy source after manifests.
COPY services/core/src ./services/core/src
COPY services/parser/src ./services/parser/src
COPY services/api/src ./services/api/src

WORKDIR /app/services/parser
RUN uv sync --frozen --no-dev

CMD ["uv", "run", "--no-dev", "python", "-m", "card_reader_parser.main"]
