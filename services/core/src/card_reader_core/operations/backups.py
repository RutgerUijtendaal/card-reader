from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import sqlite3
import subprocess
import tarfile
import time
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

from card_reader_core.config.settings import REPO_ROOT

ARCHIVE_VERSION = 1
DEFAULT_HEALTHCHECK_URL = "http://127.0.0.1:8000/health"
BACKUP_PREFIX = "card-reader"


class BackupError(RuntimeError):
    pass


@dataclass(frozen=True)
class RuntimePaths:
    app_data_dir: Path
    public_app_data_dir: Path
    database_path: Path

    @classmethod
    def from_environment(cls) -> RuntimePaths:
        app_data_dir = Path(os.getenv("CARD_READER_APP_DATA_DIR", str(REPO_ROOT / "storage"))).expanduser()
        public_app_data_dir = Path(
            os.getenv("CARD_READER_PUBLIC_APP_DATA_DIR", str(app_data_dir / "public"))
        ).expanduser()
        database_env = Path(os.getenv("CARD_READER_DATABASE_PATH", "card_reader.db")).expanduser()
        database_path = database_env if database_env.is_absolute() else app_data_dir / database_env
        return cls(
            app_data_dir=app_data_dir.resolve(),
            public_app_data_dir=public_app_data_dir.resolve(),
            database_path=database_path.resolve(),
        )


@dataclass(frozen=True)
class BackupArtifact:
    archive_path: Path
    manifest: dict[str, Any]


@dataclass(frozen=True)
class ValidatedBackup:
    manifest: dict[str, Any]
    extracted_root: Path
    database_snapshot_path: Path
    app_data_root: Path
    public_root: Path


@dataclass(frozen=True)
class ComposeConfig:
    command: str
    compose_file: Path
    project_dir: Path


def create_backup_archive(
    *,
    runtime_paths: RuntimePaths,
    backup_root: Path,
    include_logs: bool = False,
    prefix: str = BACKUP_PREFIX,
    timestamp: datetime | None = None,
) -> BackupArtifact:
    _validate_runtime_paths(runtime_paths)
    backup_root = backup_root.resolve()
    backup_root.mkdir(parents=True, exist_ok=True)

    created_at = timestamp or datetime.now(UTC)
    stamp = created_at.strftime("%Y%m%d-%H%M%S")
    archive_name = f"{prefix}-{stamp}.tar.gz"
    backup_id = f"{prefix}-{stamp}"

    temp_dir = _make_work_dir(backup_root, backup_id)
    try:
        staging_root = temp_dir / "staging"
        content_root = staging_root / "content"
        content_root.mkdir(parents=True, exist_ok=True)

        db_root = content_root / "db"
        db_root.mkdir(parents=True, exist_ok=True)
        db_snapshot_path = db_root / runtime_paths.database_path.name
        _snapshot_sqlite_database(runtime_paths.database_path, db_snapshot_path)

        app_data_root = content_root / "app_data"
        public_root = content_root / "public"
        _copy_directory_contents(runtime_paths.app_data_dir / "uploads", app_data_root / "uploads", required=False)
        _copy_directory_contents(
            runtime_paths.app_data_dir / "maintenance",
            app_data_root / "maintenance",
            required=False,
        )
        _copy_directory_contents(runtime_paths.public_app_data_dir / "images", public_root / "images", required=True)
        _copy_directory_contents(runtime_paths.public_app_data_dir / "symbols", public_root / "symbols", required=True)
        if include_logs:
            _copy_directory_contents(runtime_paths.app_data_dir / "logs", app_data_root / "logs", required=False)

        manifest = _build_manifest(
            runtime_paths=runtime_paths,
            content_root=content_root,
            backup_id=backup_id,
            created_at=created_at,
            include_logs=include_logs,
        )
        manifest_path = staging_root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

        temp_archive_path = temp_dir / f"{archive_name}.tmp"
        final_archive_path = backup_root / archive_name
        _write_archive(staging_root, temp_archive_path)
        temp_archive_path.replace(final_archive_path)
        return BackupArtifact(archive_path=final_archive_path, manifest=manifest)
    finally:
        _cleanup_work_dir(temp_dir)


def validate_backup_archive(archive_path: Path) -> dict[str, Any]:
    extraction_root = _make_work_dir(archive_path.resolve().parent, "card-reader-validate")
    try:
        _extract_archive(archive_path, extraction_root)
        validated = _validate_extracted_backup(extraction_root)
        return validated.manifest
    finally:
        _cleanup_work_dir(extraction_root)


def restore_backup_archive(
    *,
    archive_path: Path,
    runtime_paths: RuntimePaths,
    backup_root: Path | None = None,
    include_logs: bool = False,
    compose_config: ComposeConfig | None = None,
    healthcheck_url: str | None = DEFAULT_HEALTHCHECK_URL,
    healthcheck_attempts: int = 10,
    healthcheck_delay_seconds: float = 2.0,
) -> Path | None:
    extraction_root = _make_work_dir(archive_path.resolve().parent, "card-reader-restore")
    try:
        _extract_archive(archive_path, extraction_root)
        validated = _validate_extracted_backup(extraction_root)

        if compose_config is not None:
            _run_compose(compose_config, "down")

        safety_archive_path: Path | None = None
        safety_backup_error: Exception | None = None
        try:
            if backup_root is not None:
                try:
                    safety_backup = create_backup_archive(
                        runtime_paths=runtime_paths,
                        backup_root=backup_root,
                        include_logs=include_logs,
                        prefix="pre-restore-card-reader",
                    )
                except Exception as exc:
                    safety_backup_error = exc
                else:
                    safety_archive_path = safety_backup.archive_path

            _replace_live_runtime(runtime_paths, validated)

            if compose_config is not None:
                _run_compose(compose_config, "up", "-d", "--remove-orphans")

            if healthcheck_url is not None:
                _wait_for_healthcheck(
                    healthcheck_url,
                    attempts=healthcheck_attempts,
                    delay_seconds=healthcheck_delay_seconds,
                )
        except Exception:
            if compose_config is not None:
                try:
                    _run_compose(compose_config, "up", "-d", "--remove-orphans")
                except Exception:
                    pass
            if safety_backup_error is not None:
                try:
                    raise
                except Exception as restore_error:
                    restore_error.add_note(
                        "Pre-restore safety backup creation failed before restore: "
                        f"{safety_backup_error!r}"
                    )
                    raise
            raise

        return safety_archive_path
    finally:
        _cleanup_work_dir(extraction_root)


def default_compose_config() -> ComposeConfig:
    return ComposeConfig(
        command=os.getenv("CARD_READER_COMPOSE_CMD", "docker-compose"),
        compose_file=Path(
            os.getenv("CARD_READER_COMPOSE_FILE", str(REPO_ROOT / "docker-compose.yml"))
        ).resolve(),
        project_dir=Path(os.getenv("CARD_READER_PROJECT_DIR", str(REPO_ROOT))).resolve(),
    )


def _validate_runtime_paths(runtime_paths: RuntimePaths) -> None:
    if not runtime_paths.app_data_dir.exists():
        raise BackupError(f"App data directory does not exist: {runtime_paths.app_data_dir}")
    if not runtime_paths.public_app_data_dir.exists():
        raise BackupError(f"Public app data directory does not exist: {runtime_paths.public_app_data_dir}")
    if not runtime_paths.database_path.exists():
        raise BackupError(f"Database file does not exist: {runtime_paths.database_path}")
    if not (runtime_paths.public_app_data_dir / "images").exists():
        raise BackupError(f"Images directory does not exist: {runtime_paths.public_app_data_dir / 'images'}")
    if not (runtime_paths.public_app_data_dir / "symbols").exists():
        raise BackupError(f"Symbols directory does not exist: {runtime_paths.public_app_data_dir / 'symbols'}")


def _snapshot_sqlite_database(source_path: Path, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    source_db = sqlite3.connect(str(source_path))
    target_db = sqlite3.connect(str(target_path))
    try:
        source_db.backup(target_db)
    finally:
        target_db.close()
        source_db.close()

    snapshot_db = sqlite3.connect(str(target_path))
    try:
        result = snapshot_db.execute("PRAGMA integrity_check").fetchone()
    finally:
        snapshot_db.close()
    if result is None or result[0] != "ok":
        raise BackupError(f"SQLite integrity check failed for snapshot: {target_path}")


def _copy_directory_contents(source_dir: Path, target_dir: Path, *, required: bool) -> None:
    if not source_dir.exists():
        if required:
            raise BackupError(f"Required directory does not exist: {source_dir}")
        target_dir.mkdir(parents=True, exist_ok=True)
        return
    if not source_dir.is_dir():
        raise BackupError(f"Expected directory but found non-directory path: {source_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)
    for child in source_dir.iterdir():
        destination = target_dir / child.name
        if child.is_dir():
            shutil.copytree(child, destination)
        else:
            shutil.copy2(child, destination)


def _build_manifest(
    *,
    runtime_paths: RuntimePaths,
    content_root: Path,
    backup_id: str,
    created_at: datetime,
    include_logs: bool,
) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in sorted(content_root.rglob("*")):
        if not path.is_file():
            continue
        files.append(
            {
                "path": path.relative_to(content_root).as_posix(),
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )

    return {
        "archive_version": ARCHIVE_VERSION,
        "backup_id": backup_id,
        "created_at": created_at.isoformat(),
        "app_version": _read_app_version(),
        "include_logs": include_logs,
        "source_paths": {
            "app_data_dir": str(runtime_paths.app_data_dir),
            "public_app_data_dir": str(runtime_paths.public_app_data_dir),
            "database_path": str(runtime_paths.database_path),
        },
        "files": files,
    }


def _read_app_version() -> str | None:
    version_path = REPO_ROOT / "VERSION"
    if not version_path.exists():
        return None
    version = version_path.read_text(encoding="utf-8").strip()
    return version or None


def _write_archive(staging_root: Path, archive_path: Path) -> None:
    with tarfile.open(archive_path, "w:gz") as archive:
        for path in sorted(staging_root.rglob("*")):
            archive.add(path, arcname=path.relative_to(staging_root).as_posix())


def _extract_archive(archive_path: Path, extraction_root: Path) -> None:
    if not archive_path.exists():
        raise BackupError(f"Backup archive does not exist: {archive_path}")
    with tarfile.open(archive_path, "r:gz") as archive:
        archive.extractall(extraction_root, filter="data")


def _validate_extracted_backup(extraction_root: Path) -> ValidatedBackup:
    manifest_path = extraction_root / "manifest.json"
    if not manifest_path.exists():
        raise BackupError("Backup manifest is missing.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    content_root = extraction_root / "content"
    if not content_root.exists():
        raise BackupError("Backup content directory is missing.")

    files = manifest.get("files")
    if not isinstance(files, list):
        raise BackupError("Backup manifest is missing the files list.")

    manifest_paths: set[str] = set()
    for entry in files:
        path_value = entry.get("path")
        checksum = entry.get("sha256")
        if not isinstance(path_value, str) or not isinstance(checksum, str):
            raise BackupError("Backup manifest contains an invalid file entry.")
        if path_value in manifest_paths:
            raise BackupError(f"Backup manifest contains a duplicate file entry: {path_value}")
        manifest_paths.add(path_value)
        file_path = content_root / path_value
        if not file_path.exists():
            raise BackupError(f"Backup file is missing: {path_value}")
        if _sha256(file_path) != checksum:
            raise BackupError(f"Checksum mismatch for backup file: {path_value}")

    extracted_paths = {path.relative_to(content_root).as_posix() for path in content_root.rglob("*") if path.is_file()}
    unexpected_paths = sorted(extracted_paths - manifest_paths)
    if unexpected_paths:
        raise BackupError(f"Backup contains unexpected files: {', '.join(unexpected_paths)}")

    db_dir = content_root / "db"
    database_files = sorted(path for path in db_dir.glob("*") if path.is_file())
    if len(database_files) != 1:
        raise BackupError("Backup must contain exactly one database snapshot.")
    with sqlite3.connect(database_files[0]) as snapshot_db:
        result = snapshot_db.execute("PRAGMA integrity_check").fetchone()
    if result is None or result[0] != "ok":
        raise BackupError("Backup database snapshot failed integrity validation.")

    return ValidatedBackup(
        manifest=manifest,
        extracted_root=extraction_root,
        database_snapshot_path=database_files[0],
        app_data_root=content_root / "app_data",
        public_root=content_root / "public",
    )


def _replace_live_runtime(runtime_paths: RuntimePaths, validated: ValidatedBackup) -> None:
    runtime_paths.database_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_paths.app_data_dir.mkdir(parents=True, exist_ok=True)
    runtime_paths.public_app_data_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(validated.database_snapshot_path, runtime_paths.database_path)
    _replace_directory(runtime_paths.app_data_dir / "uploads", validated.app_data_root / "uploads")
    _replace_directory(runtime_paths.app_data_dir / "maintenance", validated.app_data_root / "maintenance")
    if (validated.app_data_root / "logs").exists():
        _replace_directory(runtime_paths.app_data_dir / "logs", validated.app_data_root / "logs")
    _replace_directory(runtime_paths.public_app_data_dir / "images", validated.public_root / "images")
    _replace_directory(runtime_paths.public_app_data_dir / "symbols", validated.public_root / "symbols")


def _replace_directory(target_dir: Path, source_dir: Path) -> None:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)


def _run_compose(compose_config: ComposeConfig, *args: str) -> None:
    command = _split_command(compose_config.command)
    command.extend(["-f", str(compose_config.compose_file), *args])
    subprocess.run(
        command,
        cwd=compose_config.project_dir,
        check=True,
    )


def _split_command(command: str) -> list[str]:
    parts = shlex.split(command, posix=os.name != "nt")
    if not parts:
        raise BackupError("Compose command is empty.")
    return parts


def _wait_for_healthcheck(url: str, *, attempts: int, delay_seconds: float) -> None:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            with urlopen(url, timeout=5) as response:
                if 200 <= response.status < 300:
                    return
        except URLError as error:
            last_error = error
        time.sleep(delay_seconds)
    raise BackupError(f"Healthcheck did not recover: {url}") from last_error


def _sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with file_path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def _make_work_dir(parent_dir: Path, prefix: str) -> Path:
    parent_dir.mkdir(parents=True, exist_ok=True)
    work_dir = parent_dir / f".{prefix}-{uuid4().hex[:8]}"
    work_dir.mkdir(parents=True, exist_ok=False)
    return work_dir


def _cleanup_work_dir(work_dir: Path) -> None:
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
