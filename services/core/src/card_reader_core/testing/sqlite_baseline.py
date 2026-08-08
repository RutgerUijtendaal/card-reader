from __future__ import annotations

from collections.abc import Collection
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from django.db import connections

_TEST_STORAGE_MARKER_NAME = ".card-reader-sqlite-test-storage"
_TEST_STORAGE_MARKER_CONTENT = "owned by card-reader test isolation\n"


def mark_sqlite_test_storage(storage_root: Path) -> None:
    resolved_root = storage_root.resolve()
    if not resolved_root.is_dir() or resolved_root.is_symlink():
        raise RuntimeError("The test storage root must be an existing real directory.")
    marker_path = resolved_root / _TEST_STORAGE_MARKER_NAME
    marker_path.write_text(_TEST_STORAGE_MARKER_CONTENT, encoding="utf-8")


class SqliteTestBaseline:
    """Restore a migrated SQLite database and its runtime files between tests."""

    def __init__(
        self,
        *,
        storage_root: Path,
        database_alias: str = "default",
        preserved_runtime_names: Collection[str] = (),
    ) -> None:
        connection = connections[database_alias]
        if connection.vendor != "sqlite":
            raise RuntimeError("SqliteTestBaseline requires a SQLite database connection.")

        database_name = connection.settings_dict["NAME"]
        if not isinstance(database_name, str) or database_name == ":memory:":
            raise RuntimeError("SqliteTestBaseline requires a file-backed SQLite database.")

        self._database_path = Path(database_name).resolve()
        self._storage_root = storage_root.resolve()
        self._preserved_runtime_names = frozenset(preserved_runtime_names)
        self._validate_paths()

        self._baseline_directory = TemporaryDirectory(prefix="card-reader-test-baseline-")
        baseline_root = Path(self._baseline_directory.name)
        self._database_snapshot = baseline_root / "database.sqlite3"
        self._storage_snapshot = baseline_root / "storage"
        self._storage_snapshot.mkdir()

        connections.close_all()
        shutil.copy2(self._database_path, self._database_snapshot)
        self._copy_runtime_files(self._storage_root, self._storage_snapshot)

    def restore(self) -> None:
        self._validate_storage_ownership()
        connections.close_all()
        self._remove_sqlite_files()
        shutil.copy2(self._database_snapshot, self._database_path)
        self._clear_runtime_files()
        self._copy_runtime_files(self._storage_snapshot, self._storage_root)

    def close(self) -> None:
        connections.close_all()
        self._baseline_directory.cleanup()

    def _validate_paths(self) -> None:
        self._validate_storage_ownership()
        if self._database_path.parent != self._storage_root:
            raise RuntimeError("The test SQLite database must live directly in the test storage root.")
        if not self._database_path.is_file() or self._database_path.is_symlink():
            raise RuntimeError("The test SQLite database must be an existing real file.")
        if self._database_path.name in self._preserved_runtime_names:
            raise RuntimeError("The SQLite database cannot be a preserved runtime path.")

    def _validate_storage_ownership(self) -> None:
        if not self._storage_root.is_dir() or self._storage_root.is_symlink():
            raise RuntimeError("The test storage root must be an existing real directory.")
        marker_path = self._storage_root / _TEST_STORAGE_MARKER_NAME
        if not marker_path.is_file() or marker_path.is_symlink():
            raise RuntimeError("The test storage root is missing its ownership marker.")
        if marker_path.read_text(encoding="utf-8") != _TEST_STORAGE_MARKER_CONTENT:
            raise RuntimeError("The test storage root ownership marker is invalid.")

    def _remove_sqlite_files(self) -> None:
        for suffix in ("", "-journal", "-shm", "-wal"):
            candidate = Path(f"{self._database_path}{suffix}")
            if candidate.exists():
                candidate.unlink()

    def _clear_runtime_files(self) -> None:
        for child in self._storage_root.iterdir():
            if child.name == self._database_path.name:
                continue
            if child.name in self._preserved_runtime_names:
                continue
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()

    def _copy_runtime_files(self, source_root: Path, destination_root: Path) -> None:
        for child in source_root.iterdir():
            if source_root == self._storage_root and child.name == self._database_path.name:
                continue
            if child.name in self._preserved_runtime_names:
                continue
            destination = destination_root / child.name
            if child.is_dir() and not child.is_symlink():
                shutil.copytree(child, destination)
            else:
                shutil.copy2(child, destination, follow_symlinks=False)
