# Card Reader Monorepo

Backend-first card parsing platform with Vue/Tauri frontend scaffolding.

## Prerequisites
Install these before running bootstrap:

- `Node.js` 22+
- `pnpm` 10+
- `Python` 3.12+
- `uv` (Astral)

Linux/WSL install examples:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs python3.12 python3.12-venv python3-pip
npm install -g pnpm
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify:

```bash
node --version
pnpm --version
python --version
uv --version
```

## Bootstrap

```bash
./scripts/bootstrap.sh --node --python
```

## Development

```bash
./scripts/dev.sh
```

Or run specific services:

```bash
pnpm --filter @card-reader/api dev
pnpm --filter @card-reader/worker dev
pnpm --filter @card-reader/web dev
pnpm --filter @card-reader/desktop dev
```
