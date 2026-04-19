from __future__ import annotations

import os
import subprocess
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from card_reader_core.database.connection import DATABASE_PATH, engine, initialize_database
from ..database_migrations import run_migrations_to_head
from ..seeds import run_registered_seeds
from card_reader_core.settings import settings


@dataclass(slots=True)
class MaintenanceResult:
    message: str
    removed_paths: list[str]


@dataclass(slots=True)
class OpenStorageLocationResult:
    message: str
    path: str


class MaintenanceService:
    def open_storage_location(self) -> OpenStorageLocationResult:
        target = settings.storage_root_dir.resolve()
        target.mkdir(parents=True, exist_ok=True)
        opened = False
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(target))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target)])
            opened = True
        except Exception:
            opened = False

        return OpenStorageLocationResult(
            message=(
                "Opened storage location in file explorer."
                if opened
                else "Storage location resolved. Could not launch file explorer in this environment."
            ),
            path=str(target),
        )

    def rebuild_database(self) -> MaintenanceResult:
        removed_paths: list[str] = []

        engine.dispose()

        db_related_paths = [
            DATABASE_PATH,
            DATABASE_PATH.with_name(f"{DATABASE_PATH.name}-shm"),
            DATABASE_PATH.with_name(f"{DATABASE_PATH.name}-wal"),
        ]
        for path in db_related_paths:
            if path.exists():
                path.unlink()
                removed_paths.append(str(path))

        initialize_database()
        run_migrations_to_head()
        run_registered_seeds(force=False)

        return MaintenanceResult(
            message="Database rebuilt and migrated to latest schema.",
            removed_paths=removed_paths,
        )

    def clear_storage_data(self, *, include_images: bool) -> MaintenanceResult:
        storage_root = settings.storage_root_dir.resolve()
        candidate_paths = [
            storage_root / "uploads",
            settings.debug_crops_dir.resolve(),
            storage_root / "logs",
        ]
        if include_images:
            candidate_paths.append(settings.image_store_dir.resolve())

        removed_paths: list[str] = []
        for path in candidate_paths:
            safe_path = path.resolve()
            if not self._is_within_storage_root(storage_root, safe_path):
                continue
            if safe_path.exists():
                shutil.rmtree(safe_path)
                removed_paths.append(str(safe_path))

        initialize_database()
        (settings.storage_root_dir / "uploads").mkdir(parents=True, exist_ok=True)
        settings.debug_crops_dir.mkdir(parents=True, exist_ok=True)
        (settings.storage_root_dir / "logs").mkdir(parents=True, exist_ok=True)

        return MaintenanceResult(
            message=(
                "Storage data cleared."
                if include_images
                else "Storage debug data cleared (images preserved)."
            ),
            removed_paths=removed_paths,
        )

    @staticmethod
    def _is_within_storage_root(storage_root: Path, target: Path) -> bool:
        try:
            target.relative_to(storage_root)
            return True
        except ValueError:
            return False


