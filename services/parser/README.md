# Card Reader Parser

`services/parser` is the background parser process. It claims queued import items, runs OCR/parser
logic, and writes parsed cards, versions, images, results, and metadata through the core Django data
layer.

## Runtime

The parser boots Django with:

```text
DJANGO_SETTINGS_MODULE=card_reader_core.django_settings
```

It imports `card_reader_core` models, repositories, and services. It does not import API views,
serializers, URLs, DRF settings, or API-only services.

## Commands

Run the parser locally:

```bash
uv run --project . python -m card_reader_parser.main
```

Run package scripts:

```bash
pnpm --filter @card-reader/parser dev
pnpm --filter @card-reader/parser test
pnpm --filter @card-reader/parser lint
pnpm --filter @card-reader/parser typecheck
```

## Docker

The parser container shares the API data volume and starts after the API health check passes. The API
container owns migration and seed startup. The parser assumes the database schema is ready.

The locked PaddlePaddle build supports native parser development on Windows x86_64, Linux x86_64,
and macOS ARM64 with Python 3.12 or 3.13. The container defaults to `linux/amd64`, including on
Apple Silicon through Docker Desktop emulation.
