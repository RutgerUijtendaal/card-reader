from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tarfile

import pytest

from card_reader_core.operations.backups import (
    BackupError,
    ComposeConfig,
    RuntimePaths,
    _run_compose,
    create_backup_archive,
    restore_backup_archive,
    validate_backup_archive,
)


def test_create_backup_archive_captures_expected_runtime(tmp_path: Path) -> None:
    runtime_paths = _build_runtime(tmp_path / "runtime")
    backup_root = tmp_path / "backups"

    artifact = create_backup_archive(runtime_paths=runtime_paths, backup_root=backup_root)

    assert artifact.archive_path.exists()
    manifest = validate_backup_archive(artifact.archive_path)
    file_paths = {entry["path"] for entry in manifest["files"]}
    assert f"db/{runtime_paths.database_path.name}" in file_paths
    assert "app_data/uploads/upload.txt" in file_paths
    assert "app_data/maintenance/task.txt" in file_paths
    assert "public/images/card.png" in file_paths
    assert "public/symbols/symbol.svg" in file_paths

    with tarfile.open(artifact.archive_path, "r:gz") as archive:
        member = archive.extractfile("manifest.json")
        assert member is not None
        saved_manifest = json.loads(member.read().decode("utf-8"))
    assert saved_manifest["app_version"] is not None
    assert saved_manifest["include_logs"] is False


def test_create_backup_archive_can_include_logs(tmp_path: Path) -> None:
    runtime_paths = _build_runtime(tmp_path / "runtime")
    artifact = create_backup_archive(
        runtime_paths=runtime_paths,
        backup_root=tmp_path / "backups",
        include_logs=True,
    )

    manifest = validate_backup_archive(artifact.archive_path)
    file_paths = {entry["path"] for entry in manifest["files"]}
    assert "app_data/logs/api.log" in file_paths
    assert manifest["include_logs"] is True


def test_create_backup_archive_fails_when_required_public_dir_is_missing(tmp_path: Path) -> None:
    runtime_paths = _build_runtime(tmp_path / "runtime")
    (runtime_paths.public_app_data_dir / "images").rename(runtime_paths.public_app_data_dir / "images-old")

    with pytest.raises(BackupError, match="Images directory does not exist"):
        create_backup_archive(runtime_paths=runtime_paths, backup_root=tmp_path / "backups")


def test_restore_backup_archive_restores_runtime_state(tmp_path: Path) -> None:
    source_runtime = _build_runtime(tmp_path / "source-runtime")
    archive = create_backup_archive(runtime_paths=source_runtime, backup_root=tmp_path / "backups").archive_path

    target_runtime = _build_runtime(tmp_path / "target-runtime")
    _write_text(target_runtime.app_data_dir / "uploads" / "upload.txt", "target upload")
    _write_text(target_runtime.public_app_data_dir / "images" / "card.png", "target image")

    safety_archive = restore_backup_archive(
        archive_path=archive,
        runtime_paths=target_runtime,
        backup_root=tmp_path / "safety",
        include_logs=True,
        compose_config=None,
        healthcheck_url=None,
    )

    assert safety_archive is not None
    assert safety_archive.exists()
    assert _read_count(target_runtime.database_path) == 1
    assert (target_runtime.app_data_dir / "uploads" / "upload.txt").read_text(encoding="utf-8") == "upload"
    assert (target_runtime.public_app_data_dir / "images" / "card.png").read_text(encoding="utf-8") == "image"
    assert (target_runtime.public_app_data_dir / "symbols" / "symbol.svg").read_text(encoding="utf-8") == "symbol"


def test_restore_backup_archive_recovers_when_safety_backup_fails(tmp_path: Path) -> None:
    source_runtime = _build_runtime(tmp_path / "source-runtime")
    archive = create_backup_archive(runtime_paths=source_runtime, backup_root=tmp_path / "backups").archive_path

    target_runtime = _build_runtime(tmp_path / "target-runtime")
    _write_text(target_runtime.database_path, "not-a-sqlite-db")
    _write_text(target_runtime.app_data_dir / "uploads" / "upload.txt", "target upload")
    _write_text(target_runtime.public_app_data_dir / "images" / "card.png", "target image")

    safety_archive = restore_backup_archive(
        archive_path=archive,
        runtime_paths=target_runtime,
        backup_root=tmp_path / "safety",
        include_logs=True,
        compose_config=None,
        healthcheck_url=None,
    )

    assert safety_archive is None
    assert _read_count(target_runtime.database_path) == 1
    assert (target_runtime.app_data_dir / "uploads" / "upload.txt").read_text(encoding="utf-8") == "upload"
    assert (target_runtime.public_app_data_dir / "images" / "card.png").read_text(encoding="utf-8") == "image"
    assert (target_runtime.public_app_data_dir / "symbols" / "symbol.svg").read_text(encoding="utf-8") == "symbol"


def test_restore_backup_archive_rejects_checksum_mismatch(tmp_path: Path) -> None:
    runtime_paths = _build_runtime(tmp_path / "runtime")
    archive_path = create_backup_archive(
        runtime_paths=runtime_paths,
        backup_root=tmp_path / "backups",
    ).archive_path

    tampered_archive_path = tmp_path / "tampered.tar.gz"
    with tarfile.open(archive_path, "r:gz") as source_archive:
        source_archive.extractall(tmp_path / "tampered")
    _write_text(tmp_path / "tampered" / "content" / "public" / "images" / "card.png", "tampered")
    with tarfile.open(tampered_archive_path, "w:gz") as tampered_archive:
        for path in sorted((tmp_path / "tampered").rglob("*")):
            tampered_archive.add(path, arcname=path.relative_to(tmp_path / "tampered").as_posix())

    with pytest.raises(BackupError, match="Checksum mismatch"):
        restore_backup_archive(
            archive_path=tampered_archive_path,
            runtime_paths=_build_runtime(tmp_path / "restore-runtime"),
            backup_root=tmp_path / "safety",
            compose_config=None,
            healthcheck_url=None,
        )


def test_restore_backup_archive_rejects_unexpected_files(tmp_path: Path) -> None:
    runtime_paths = _build_runtime(tmp_path / "runtime")
    archive_path = create_backup_archive(
        runtime_paths=runtime_paths,
        backup_root=tmp_path / "backups",
    ).archive_path

    tampered_archive_path = tmp_path / "tampered-extra-file.tar.gz"
    with tarfile.open(archive_path, "r:gz") as source_archive:
        source_archive.extractall(tmp_path / "tampered-extra")
    _write_text(tmp_path / "tampered-extra" / "content" / "public" / "images" / "unexpected.txt", "injected")
    with tarfile.open(tampered_archive_path, "w:gz") as tampered_archive:
        for path in sorted((tmp_path / "tampered-extra").rglob("*")):
            tampered_archive.add(path, arcname=path.relative_to(tmp_path / "tampered-extra").as_posix())

    with pytest.raises(BackupError, match="Backup contains unexpected files"):
        restore_backup_archive(
            archive_path=tampered_archive_path,
            runtime_paths=_build_runtime(tmp_path / "restore-runtime"),
            backup_root=tmp_path / "safety",
            compose_config=None,
            healthcheck_url=None,
        )


def test_run_compose_supports_two_word_compose_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def fake_run(command: list[str], *, cwd: Path, check: bool) -> None:
        captured["command"] = command
        captured["cwd"] = cwd
        captured["check"] = check

    monkeypatch.setattr("card_reader_core.operations.backups.subprocess.run", fake_run)

    compose_config = ComposeConfig(
        command="docker compose",
        compose_file=tmp_path / "docker-compose.yml",
        project_dir=tmp_path,
    )

    _run_compose(compose_config, "down")

    assert captured["command"] == ["docker", "compose", "-f", str(compose_config.compose_file), "down"]
    assert captured["cwd"] == tmp_path
    assert captured["check"] is True


def _build_runtime(root: Path) -> RuntimePaths:
    app_data_dir = root
    public_dir = root / "public"
    database_path = root / "card_reader.db"

    (app_data_dir / "uploads").mkdir(parents=True, exist_ok=True)
    (app_data_dir / "maintenance").mkdir(parents=True, exist_ok=True)
    (app_data_dir / "logs").mkdir(parents=True, exist_ok=True)
    (public_dir / "images").mkdir(parents=True, exist_ok=True)
    (public_dir / "symbols").mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE cards (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        connection.execute("INSERT INTO cards (name) VALUES (?)", ("Arcane Owl",))
        connection.commit()

    _write_text(app_data_dir / "uploads" / "upload.txt", "upload")
    _write_text(app_data_dir / "maintenance" / "task.txt", "task")
    _write_text(app_data_dir / "logs" / "api.log", "log")
    _write_text(public_dir / "images" / "card.png", "image")
    _write_text(public_dir / "symbols" / "symbol.svg", "symbol")

    return RuntimePaths(
        app_data_dir=app_data_dir,
        public_app_data_dir=public_dir,
        database_path=database_path,
    )


def _read_count(database_path: Path) -> int:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute("SELECT COUNT(*) FROM cards").fetchone()
    assert row is not None
    return int(row[0])


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
