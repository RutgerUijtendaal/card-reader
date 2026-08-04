# Card Reader

Card Reader is a monorepo for importing, parsing, reviewing, and browsing card data.
It combines a Django API, a shared Python domain layer, an OCR/parser worker, a Vue web app, and a
supporting project automation.

# Feature tracker

https://trello.com/b/sCM4JM5V/cards

## What is in this repo

- `frontend`: Vue 3 + Vite frontend for gallery, imports, review, settings, and auth flows
- `services/core`: shared Django models, migrations, repositories, services, settings, and storage
- `services/api`: Django + DRF API service
- `services/parser`: background OCR/parser worker
- `services/integration`: integration tests across API, parser, and core
- `scripts`: project-specific maintenance and development automation

## Stack

- Monorepo: `pnpm` workspaces + `turbo`
- Frontend: Vue 3, Vite, TypeScript
- Backend: Django, Django REST Framework
- Python tooling: `uv`, `pytest`, `ruff`, `mypy`
- OCR/CV: PaddleOCR, PaddleX, OpenCV
- Default persistence: SQLite

## Prerequisites

- [Node.js 22+](https://nodejs.org/en/download)
- [`pnpm` 10+](https://pnpm.io/installation)
- Python 3.12 or 3.13 (`.python-version` pins development to 3.12)
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) for Python and workspace dependency management
- [Docker](https://docs.docker.com/get-started/get-docker/) is optional and only needed for container workflows

These are system tools. `pnpm bootstrap:dev` installs the JavaScript and Python project dependencies
after they are available. Check the installed tools and versions before bootstrapping:

```bash
pnpm preflight
```

Native full-workspace development is supported on Windows x86_64, Linux x86_64, and Apple Silicon
macOS. PaddlePaddle does not provide every OS/architecture combination used by the parser. On Intel
macOS or ARM Linux, run the Python services with Docker Compose and the frontend separately instead
of using `pnpm setup` and `pnpm dev`; ARM Linux hosts must have amd64 container emulation enabled.

## Quick Start

For a new checkout, sign in with a staff account or an account assigned the Developer role, open
**Settings → Developer Data**, generate a bootstrap code, then run:

```bash
pnpm bootstrap:dev
```

The command installs dependencies, migrates an empty local database, downloads and verifies the
bundle pinned by `dev-data.lock.json`, imports its records and media, prompts for local admin
credentials, and runs a readiness check.

Offline onboarding, reset behavior, and staff publication are documented in
[Developer data](docs/developer-data.md).

Start the default development stack:

```bash
pnpm dev
```

That starts:

- the API
- the parser worker
- the developer-data builder worker
- the web app

## Local Development

Useful commands from the repo root:

```bash
pnpm setup
pnpm bootstrap:dev
pnpm bootstrap:dev:reset
pnpm deps:js
pnpm deps:py
pnpm dev
pnpm dev:all
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

## Documentation

Feature guides, operational documentation, and technical references are indexed in
[docs/README.md](docs/README.md).

## Configuration

Runtime configuration is provided through `CARD_READER_*` environment variables.

For Docker or production-style local runs:

```bash
cp .env.example .env
```

Important settings in `./.env.example`:

- `CARD_READER_DJANGO_SECRET_KEY`
- `CARD_READER_ALLOWED_HOSTS`
- `CARD_READER_CSRF_TRUSTED_ORIGINS`
- `CARD_READER_CORS_ORIGINS`
- `CARD_READER_DATABASE_PATH`
- `CARD_READER_PARSER_PLATFORM`

## Auth Model

Auth is always enabled.

- Card gallery and card assets are public
- Public deck detail and deck TTS export are available to any viewer who can access the deck
- Import jobs, review, administrative settings APIs, catalog, templates, and CSV exports require a staff user
- Developer-data metadata, direct downloads, and bootstrap-code creation require an active staff
  account or an active account assigned the Developer role
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
- `developer-data-builder`: processes queued staff builds outside Gunicorn

The API and parser share a Docker volume mounted at `/var/lib/card-reader`.
The parser defaults to a `linux/amd64` container so the same locked PaddlePaddle build works on
x86_64 hosts and through Docker Desktop emulation on Apple Silicon.

The default Compose file uses the Docker-managed `card_reader_data` volume. Deployments that need
explicit host storage can add the bind-mount override after setting
`CARD_READER_HOST_APP_DATA_DIR` and `CARD_READER_HOST_PUBLIC_APP_DATA_DIR`:

```bash
docker compose -f docker-compose.yml -f docker-compose.bind.yml up -d --build
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Storage

Default storage locations:

- local development: `storage/`
- Docker: the `card_reader_data` volume mounted at `/var/lib/card-reader`

Containers use `/var/lib/card-reader` consistently. `CARD_READER_APP_DATA_DIR` remains available to
native processes that need a custom storage root. Use the explicit bind-mount override when
container data must live at a known host path.
