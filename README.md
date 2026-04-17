# Card Reader Monorepo

Backend-first card parsing platform with Vue/Tauri frontend scaffolding.

## Prerequisites
Install these before running bootstrap:

- `Node.js` 22+
- `pnpm` 10+
- `Python` 3.12+
- `uv` (Astral)
- `Rust` + `cargo` (required only for Tauri desktop)
- OCR runtime note: `bootstrap` installs OCR deps for parser (`paddleocr`, `paddlepaddle`) and shared deps for core/API.

Linux/WSL install examples:

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

Verify:

```bash
node --version
pnpm --version
python --version
uv --version
cargo --version
pkg-config --modversion glib-2.0
```

Optional sanity check after bootstrap:

```bash
cd services/parser
uv run --project . python -c "import paddle, paddleocr; print('ok')"
```

## Bootstrap

```bash
./scripts/bootstrap.sh --node --python
```

## Development

```bash
./scripts/dev.sh
```

This starts API + parser + web (desktop excluded).
It also re-syncs Python dependencies for core/API/parser before starting.
Hot reload behavior in dev:
- Web (Vite): HMR enabled with polling watch (WSL-safe).
- API (Uvicorn): `--reload` enabled with polling-based file watch.
- Parser: auto-restarts on Python file changes via `watchfiles`.

Or run specific services:

```bash
pnpm --filter @card-reader/api dev
pnpm --filter @card-reader/parser dev
pnpm --filter @card-reader/core lint
pnpm --filter @card-reader/web dev
pnpm dev:all
pnpm dev:desktop
```

Known keywords are auto-seeded on first API boot (only when the `keyword` table is empty).

Manual reseed:

```bash
pnpm --filter @card-reader/api run seed:keywords
```

Edit defaults in `services/core/seeds/keywords.txt` (one keyword label per line).

## Desktop (Tauri) Prerequisites

Desktop dev requires Rust/Cargo and GTK/WebKit system libraries on Linux/WSL:

```bash
curl https://sh.rustup.rs -sSf | sh
source "$HOME/.cargo/env"
cargo --version
sudo apt install -y pkg-config libglib2.0-dev libgtk-3-dev libwebkit2gtk-4.1-dev libayatana-appindicator3-dev librsvg2-dev
```

## Storage Behavior

- Development (default): runtime data is written to `storage/` in the repo.
- Production (`CARD_READER_ENV=production`): runtime data is written to OS app data:
- Linux: `~/.local/share/card-reader`
- macOS: `~/Library/Application Support/card-reader`
- Windows: `%LOCALAPPDATA%/CardReader`

Optional override:
- Set `CARD_READER_APP_DATA_DIR=/custom/path` to force a specific storage root in any environment.

## API Logs

- API logs are written to `<storage_root>/logs/api.log`.
- In development defaults, that is `storage/logs/api.log`.
- Use this file to diagnose backend-side import failures.
