# Backup and restore

Card Reader can create recovery archives for its runtime database and stored media. This is an
operational feature: deployment automation owns the destination, schedule, retention policy, and
off-site replication. Environment-specific storage names do not belong in the application source.

## Archive contents

A backup contains:

- a consistent SQLite snapshot with an integrity check;
- uploaded files and maintenance data;
- public card images and symbol assets;
- logs only when `--include-logs` is requested;
- a manifest containing file sizes and SHA-256 checksums.

Developer-data bundles are intentionally excluded. They are reproducible, immutable artifacts and
are retained separately from runtime recovery archives.

Runtime locations are resolved from:

- `CARD_READER_APP_DATA_DIR`;
- `CARD_READER_PUBLIC_APP_DATA_DIR`;
- `CARD_READER_DATABASE_PATH`.

## Create an archive

Choose a destination appropriate for the current environment:

```bash
uv run --project . python scripts/create-backup.py --backup-root BACKUP_DIRECTORY
```

The Unix wrapper supports the same arguments and can run through the configured Compose service:

```bash
./scripts/create-backup.sh --backup-root BACKUP_DIRECTORY
```

For the Docker-managed volume, run the backup inside the API service:

```bash
CARD_READER_BACKUP_RUNNER=docker_compose \
  ./scripts/create-backup.sh --backup-root BACKUP_DIRECTORY
```

## Restore an archive

```bash
uv run --project . python scripts/restore-backup.py BACKUP_ARCHIVE
```

Restore a Docker-managed volume through the API service so the restore process can access the
volume directly:

```bash
CARD_READER_RESTORE_RUNNER=docker_compose \
  ./scripts/restore-backup.sh BACKUP_ARCHIVE
```

The Docker wrapper stops the Compose stack, restores and validates the archive, creates the safety
backup on the host, and restarts the stack with `docker compose up --wait`.

For a bind-mounted deployment, set `CARD_READER_BACKUP_COMPOSE_OVERRIDE_FILE` or
`CARD_READER_RESTORE_COMPOSE_OVERRIDE_FILE` to `docker-compose.bind.yml` so operational commands
use the same merged configuration as the running stack.

Restore validates the manifest and checksums before replacing live data. By default it stops and
restarts the Compose stack, creates a pre-restore safety archive beside the selected archive, and
waits for the API health check. Use the command's `--help` output for recovery-specific overrides.

Restore is destructive to the configured runtime paths. Confirm the environment variables and
archive before running it.
