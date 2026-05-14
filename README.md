# Card Reader

Card Reader is a monorepo for importing, parsing, reviewing, and browsing card data.
It combines a Django API, a shared Python domain layer, an OCR/parser worker, a Vue web app, and a
Tauri desktop shell.

# Feature tracker

https://trello.com/b/sCM4JM5V/cards

## What is in this repo

- `apps/web`: Vue 3 + Vite frontend for gallery, imports, review, settings, and auth flows
- `apps/desktop`: Tauri wrapper for the web/backend experience
- `services/core`: shared Django models, migrations, repositories, services, settings, and storage
- `services/api`: Django + DRF API service
- `services/parser`: background OCR/parser worker
- `services/integration`: integration tests across API, parser, and core
- `scripts`: project-specific automation for desktop Python packaging and repo versioning

## Stack

- Monorepo: `pnpm` workspaces + `turbo`
- Frontend: Vue 3, Vite, TypeScript
- Backend: Django, Django REST Framework
- Python tooling: `uv`, `pytest`, `ruff`, `mypy`
- OCR/CV: PaddleOCR, PaddleX, OpenCV
- Desktop: Tauri + Rust
- Default persistence: SQLite

## Prerequisites

- Node.js 22+
- `pnpm` 10+
- Python 3.12+
- `uv`
- Rust + Cargo for desktop development only
- Docker for containerized API/parser runs

## Quick Start

Install dependencies:

```bash
pnpm setup
```

Start the default development stack:

```bash
pnpm dev
```

That starts:

- the API
- the parser worker
- the web app

Desktop is excluded from the default loop. Use `pnpm dev:desktop` when needed.

Desktop production bundles package a managed Python runtime plus installed backend packages. The
desktop app launches the API and parser with `python -m ...` rather than frozen PyInstaller
executables.

## Local Development

Useful commands from the repo root:

```bash
pnpm setup
pnpm deps:js
pnpm deps:py
pnpm dev
pnpm dev:all
pnpm dev:desktop
pnpm lint
pnpm typecheck
pnpm test
pnpm check
```

Targeted commands:

```bash
pnpm --filter @card-reader/web dev
pnpm --filter @card-reader/api dev
pnpm --filter @card-reader/parser dev
pnpm --filter @card-reader/desktop run build:python
pnpm --filter @card-reader/integration test
pnpm --filter @card-reader/core lint
```

## Python Workspace

Python services use one shared workspace environment at the repo root.

- Sync everything: `pnpm deps:py`
- The shared virtualenv lives at `.venv/`

When you need to run a specific Python package directly:

```bash
uv run --project . --package card-reader-api python manage.py check
uv run --project . --package card-reader-parser python -m card_reader_parser.main
```

## Configuration

Runtime configuration is provided through `CARD_READER_*` environment variables.

For Docker or production-style local runs:

```bash
cp .env.example .env
```

Important settings in [.env.example](C:/Users/rutge/Documents/projects/card-reader/.env.example):

- `CARD_READER_DJANGO_SECRET_KEY`
- `CARD_READER_ALLOWED_HOSTS`
- `CARD_READER_CSRF_TRUSTED_ORIGINS`
- `CARD_READER_CORS_ORIGINS`
- `CARD_READER_AUTH_ENABLED`
- `CARD_READER_APP_DATA_DIR`
- `CARD_READER_DATABASE_PATH`

## Auth Model

Auth is enabled by default.

- Card gallery and card assets are public
- Import jobs, review, settings, catalog, templates, and exports require a staff user
- Maintenance endpoints require a superuser

Local user seed data lives at:

```text
services/api/src/card_reader_api/seeds/seed-users.local.json
```

That file is gitignored. Use `seed-users.example.json` in the same directory as the format reference.

## Docker

Start the API and parser with Docker Compose:

```bash
docker compose up -d --build
```

Current container behavior:

- `api`: runs migrations, seeds users/default data, then starts Gunicorn
- `parser`: starts the background parser and waits for the API health check

The API and parser share a Docker volume mounted at `/var/lib/card-reader`.

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Storage

Default storage locations:

- local development: `storage/`
- Docker: `/var/lib/card-reader`

Set `CARD_READER_APP_DATA_DIR` to override the storage root.

## Versioning

The root [VERSION](C:/Users/rutge/Documents/projects/card-reader/VERSION) file is the single source of truth for repo versioning.

Update every tracked manifest version together:

```bash
pnpm version:repo 0.1.8
```

Verify that all manifests match:

```bash
pnpm version:check
```

Release tags should use the `vX.Y.Z` format and match `VERSION`.
