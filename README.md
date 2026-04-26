# Card Reader Monorepo

Card Reader is a Django-backed card parsing platform with a Vue web app, a Tauri desktop shell,
and a background OCR/parser process.

## Stack

- Monorepo tooling: `pnpm` workspaces + `turbo`
- Web app: Vue 3 + Vite + TypeScript
- Desktop shell: Tauri
- Backend API: Django + Django REST Framework
- Shared backend core: Django models, migrations, repositories, services, settings, and storage
- Parser: Python background process using the core Django data layer
- Persistence: SQLite by default
- OCR/CV: PaddleOCR + OpenCV

## Prerequisites

- `Node.js` 22+
- `pnpm` 10+
- `Python` 3.12+
- `uv` (Astral)
- `Rust` + `cargo` for Tauri desktop development

Linux/WSL install example:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y \
  nodejs python3.12 python3.12-venv python3-pip \
  pkg-config libglib2.0-dev libgtk-3-dev libwebkit2gtk-4.1-dev \
  libayatana-appindicator3-dev librsvg2-dev
npm install -g pnpm
curl -LsSf https://astral.sh/uv/install.sh | sh
curl https://sh.rustup.rs -sSf | sh
source "$HOME/.cargo/env"
```

## Bootstrap

```bash
./scripts/bootstrap.sh --node --python
```

The bootstrap installs Node dependencies and syncs the Python environments for core, API, parser,
and integration tests.

## Development

```bash
./scripts/dev.sh
```

This starts the Django API, parser, and Vue web app. Desktop is excluded from the default dev loop.

Useful targeted commands:

```bash
pnpm --filter @card-reader/api dev
pnpm --filter @card-reader/parser dev
pnpm --filter @card-reader/core lint
pnpm --filter @card-reader/web dev
pnpm --filter @card-reader/integration test
pnpm dev:all
pnpm dev:desktop
```

## Backend Runtime

The API service is a Django project in `services/api`. Domain models and migrations live in
`services/core` so both the API and parser use the same data layer.

The API startup sequence runs:

```bash
python manage.py migrate_card_reader
python manage.py seed_users
python manage.py seed_defaults
python manage.py runserver 127.0.0.1:8000
```

Auth is enabled by default. The public card gallery remains accessible without login. Import jobs,
review, settings, catalog, templates, and exports require a staff user. Maintenance actions require a
superuser.

## Seed Files

Default catalog/template seeds live in `services/api/src/card_reader_api/seeds`:

- `seed-keywords.json`
- `seed-symbols.json`
- `seed-templates.json`

Local development users live in:

```text
services/api/src/card_reader_api/seeds/seed-users.local.json
```

That file is gitignored. Use `seed-users.example.json` in the same directory as the schema reference.

User seed entries use:

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

`seed_users` creates missing users and updates `is_staff` / `is_superuser` for existing users. It does
not overwrite passwords for existing users.

## Docker Deploy

Copy the environment template and set production values:

```bash
cp .env.example .env
```

Start the backend services:

```bash
docker compose up -d --build
```

The compose stack runs:

- `api`: Django migrations, user seeds, default seeds, then Gunicorn on `0.0.0.0:8000`
- `parser`: background parser process with `DJANGO_SETTINGS_MODULE=card_reader_core.django_settings`

Both services share the `card_reader_data` Docker volume at `/var/lib/card-reader`.

Production settings are controlled through `.env`:

- `CARD_READER_DJANGO_SECRET_KEY`
- `CARD_READER_ALLOWED_HOSTS`
- `CARD_READER_CSRF_TRUSTED_ORIGINS`
- `CARD_READER_CORS_ORIGINS`
- `CARD_READER_AUTH_ENABLED`

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Ansible Deploy

The webserver Ansible role owns the production user seed file:

```text
../rutgeruijtendaal.com/infra/roles/webserver/files/card-reader-users.json
```

The tracked schema example is:

```text
../rutgeruijtendaal.com/infra/roles/webserver/files/card-reader-users.example.json
```

During deploy, the role copies the private production file into the deployed app at:

```text
services/api/src/card_reader_api/seeds/seed-users.local.json
```

The generic Docker Compose deploy task only handles environment rendering, required environment
validation, and deployment file copying. Card Reader-specific file paths are declared in the
Card Reader deployment item.

## Storage

- Development storage root: `storage/`
- Docker storage root: `/var/lib/card-reader`
- Production native storage root:
  - Linux: `~/.local/share/card-reader`
  - macOS: `~/Library/Application Support/card-reader`
  - Windows: `%LOCALAPPDATA%/Card Reader`

Set `CARD_READER_APP_DATA_DIR` to force a storage root.

API logs are written to:

```text
<storage_root>/logs/api.log
```
