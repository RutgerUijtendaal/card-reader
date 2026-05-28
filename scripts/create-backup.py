#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from card_reader_core.operations.backups import RuntimePaths, create_backup_archive


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Card Reader backup archive.")
    parser.add_argument("--backup-root", required=True, help="Destination directory for backup archives.")
    parser.add_argument(
        "--include-logs",
        action="store_true",
        help="Include app logs in the backup archive.",
    )
    args = parser.parse_args()

    artifact = create_backup_archive(
        runtime_paths=RuntimePaths.from_environment(),
        backup_root=Path(args.backup_root),
        include_logs=args.include_logs,
    )
    print(artifact.archive_path)


if __name__ == "__main__":
    main()
