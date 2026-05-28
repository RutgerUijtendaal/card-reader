#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from card_reader_core.operations.backups import (
    DEFAULT_HEALTHCHECK_URL,
    RuntimePaths,
    default_compose_config,
    restore_backup_archive,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore a Card Reader backup archive.")
    parser.add_argument("archive_path", help="Path to the backup archive to restore.")
    parser.add_argument(
        "--backup-root",
        help="Destination directory for the automatic pre-restore safety backup. Defaults to the archive directory.",
    )
    parser.add_argument(
        "--include-logs",
        action="store_true",
        help="Include logs in the automatic pre-restore safety backup.",
    )
    parser.add_argument(
        "--skip-compose",
        action="store_true",
        help="Do not stop or restart the docker compose stack during restore.",
    )
    parser.add_argument(
        "--skip-healthcheck",
        action="store_true",
        help="Skip the post-restore healthcheck.",
    )
    args = parser.parse_args()

    compose_config = None if args.skip_compose else default_compose_config()
    backup_root = Path(args.backup_root) if args.backup_root else Path(args.archive_path).resolve().parent
    healthcheck_url = None if args.skip_healthcheck else DEFAULT_HEALTHCHECK_URL

    safety_archive = restore_backup_archive(
        archive_path=Path(args.archive_path),
        runtime_paths=RuntimePaths.from_environment(),
        backup_root=backup_root,
        include_logs=args.include_logs,
        compose_config=compose_config,
        healthcheck_url=healthcheck_url,
    )
    if safety_archive is not None:
        print(safety_archive)


if __name__ == "__main__":
    main()
