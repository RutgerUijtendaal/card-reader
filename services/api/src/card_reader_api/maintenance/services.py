from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from django.core.management import call_command
from django.db import connection, connections

from card_reader_api.seeds.runner import run_registered_seeds
from card_reader_core.database.connection import DATABASE_PATH, initialize_database
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
    def rebuild_database(self) -> MaintenanceResult:
        reset_paths = self._reset_database()
        initialize_database()
        call_command("migrate", interactive=False, verbosity=0)
        run_registered_seeds(force=False)
        return MaintenanceResult(
            message="Database rebuilt and migrated to latest schema.",
            removed_paths=reset_paths,
        )

    def clear_storage_data(self, *, include_images: bool) -> MaintenanceResult:
        storage_root = settings.storage_root_dir.resolve()
        candidate_paths = [storage_root / "uploads", settings.debug_crops_dir.resolve()]
        if include_images:
            candidate_paths.append(settings.image_store_dir.resolve())

        removed_paths: list[str] = []
        for path in candidate_paths:
            safe_path = path.resolve()
            if self._is_within_storage_root(storage_root, safe_path) and safe_path.exists():
                if self._safe_remove_tree(safe_path):
                    removed_paths.append(str(safe_path))

        initialize_database()
        (settings.storage_root_dir / "uploads").mkdir(parents=True, exist_ok=True)
        settings.debug_crops_dir.mkdir(parents=True, exist_ok=True)
        (settings.storage_root_dir / "logs").mkdir(parents=True, exist_ok=True)
        return MaintenanceResult(
            message="Storage data cleared." if include_images else "Storage debug data cleared (images preserved).",
            removed_paths=removed_paths,
        )

    def open_storage_location(self) -> OpenStorageLocationResult:
        target = settings.storage_root_dir.resolve()
        target.mkdir(parents=True, exist_ok=True)
        opened = self._open_path(target)
        return OpenStorageLocationResult(
            message=(
                "Opened storage location in file explorer."
                if opened
                else "Storage location resolved. Could not launch file explorer in this environment."
            ),
            path=str(target),
        )

    def _reset_database(self) -> list[str]:
        self._drop_database_schema()
        return [f"{DATABASE_PATH} (schema reset)"]

    @staticmethod
    def _drop_database_schema() -> None:
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys = OFF")
            table_names = connection.introspection.table_names(cursor)
            for table_name in table_names:
                if table_name.startswith("sqlite_"):
                    continue
                cursor.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            cursor.execute("PRAGMA foreign_keys = ON")
        connections.close_all()

    @staticmethod
    def _safe_remove_tree(path: Path) -> bool:
        try:
            shutil.rmtree(path)
        except PermissionError:
            return False
        return True

    @staticmethod
    def _is_within_storage_root(storage_root: Path, target: Path) -> bool:
        try:
            target.relative_to(storage_root)
            return True
        except ValueError:
            return False

    @staticmethod
    def _open_path(target: Path) -> bool:
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(target))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target)])
            return True
        except Exception:
            return False
