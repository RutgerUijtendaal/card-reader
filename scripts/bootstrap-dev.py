from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from card_reader_core.config.settings import REPO_ROOT, settings
from card_reader_core.database.connection import DATABASE_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a local Card Reader development database.")
    parser.add_argument("--reset", action="store_true", help="Back up and reset local data before bootstrap.")
    options, bootstrap_args = parser.parse_known_args()
    if not settings.is_dev:
        parser.error("Developer-data bootstrap is disabled outside development environments.")
    if options.reset:
        _reset_local_data()
    manage_py = REPO_ROOT / "services" / "api" / "manage.py"
    migrate_result = subprocess.run(
        [sys.executable, str(manage_py), "migrate_card_reader"],
        cwd=REPO_ROOT,
        check=False,
    )
    if migrate_result.returncode != 0:
        return migrate_result.returncode
    if bootstrap_args[:1] == ["--"]:
        bootstrap_args = bootstrap_args[1:]
    return subprocess.run(
        [sys.executable, str(manage_py), "bootstrap_dev", *bootstrap_args],
        cwd=REPO_ROOT,
        check=False,
    ).returncode


def _reset_local_data() -> None:
    database_path = DATABASE_PATH.resolve()
    storage_root = settings.storage_root_dir.resolve()
    repository_root = REPO_ROOT.resolve()
    if (
        database_path == storage_root
        or storage_root == repository_root
        or not _is_within(storage_root, repository_root)
        or not _is_within(database_path, repository_root)
    ):
        raise SystemExit("Refusing unsafe reset target configuration.")
    _reject_links(storage_root)
    targets = [path for path in (database_path, storage_root) if path.exists()]
    print("Development reset will replace:")
    for target in targets:
        print(f"  {target}")
    confirmation = input("Type RESET to create a safety backup and continue: ").strip()
    if confirmation != "RESET":
        raise SystemExit("Reset cancelled.")
    backup_root = REPO_ROOT / ".tmp" / "dev-data" / "reset-backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_root / f"before-reset-{timestamp}.tar.gz"
    with tarfile.open(backup_path, "w:gz") as archive:
        if database_path.is_file():
            archive.add(database_path, arcname=f"database/{database_path.name}")
        if storage_root.is_dir():
            archive.add(storage_root, arcname="storage", recursive=True)
    if database_path.exists():
        if not database_path.is_file() or database_path.is_symlink():
            raise SystemExit(f"Refusing to remove unexpected database target: {database_path}")
        database_path.unlink()
    if storage_root.exists():
        if not storage_root.is_dir() or storage_root.is_symlink():
            raise SystemExit(f"Refusing to remove unexpected storage target: {storage_root}")
        shutil.rmtree(storage_root)
    print(f"Safety backup created at {backup_path}")


def _reject_links(root: Path) -> None:
    if not root.exists():
        return
    if root.is_symlink():
        raise SystemExit(f"Refusing reset because storage root is a link: {root}")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise SystemExit(f"Refusing reset because storage contains a link: {path}")


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
