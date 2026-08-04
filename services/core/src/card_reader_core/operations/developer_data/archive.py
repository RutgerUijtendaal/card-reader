from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
import tempfile

from .schema import DeveloperDataManifest, DeveloperDataPayload


class DeveloperDataError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def validate_archive(archive_path: Path) -> tuple[DeveloperDataManifest, DeveloperDataPayload]:
    with extracted_archive(archive_path) as extraction_root:
        return load_extracted_bundle(extraction_root)


class extracted_archive:
    def __init__(self, archive_path: Path) -> None:
        self.archive_path = archive_path.resolve()
        self._temporary: tempfile.TemporaryDirectory[str] | None = None

    def __enter__(self) -> Path:
        if not self.archive_path.exists() or not self.archive_path.is_file():
            raise DeveloperDataError(f"Developer-data archive does not exist: {self.archive_path}")
        self._temporary = tempfile.TemporaryDirectory(prefix="card-reader-dev-data-")
        root = Path(self._temporary.name)
        try:
            with tarfile.open(self.archive_path, "r:gz") as archive:
                for member in archive.getmembers():
                    _validate_archive_member(member.name)
                archive.extractall(root, filter="data")
        except (OSError, tarfile.TarError) as exc:
            self._temporary.cleanup()
            self._temporary = None
            raise DeveloperDataError("Developer-data archive is unreadable.") from exc
        return root

    def __exit__(self, *_args: object) -> None:
        if self._temporary is not None:
            self._temporary.cleanup()


def load_extracted_bundle(extraction_root: Path) -> tuple[DeveloperDataManifest, DeveloperDataPayload]:
    manifest_path = extraction_root / "manifest.json"
    data_path = extraction_root / "data.json"
    if not manifest_path.is_file() or not data_path.is_file():
        raise DeveloperDataError("Developer-data archive is missing manifest.json or data.json.")
    try:
        manifest = DeveloperDataManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DeveloperDataError("Developer-data manifest is invalid.") from exc
    if manifest.format_version != 1:
        raise DeveloperDataError(f"Unsupported developer-data format: {manifest.format_version}")

    expected_paths: set[str] = set()
    for entry in manifest.files:
        normalized = _validate_relative_path(entry.path)
        if normalized in expected_paths:
            raise DeveloperDataError(f"Duplicate developer-data file entry: {normalized}")
        expected_paths.add(normalized)
        target = extraction_root / Path(normalized)
        if not target.is_file():
            raise DeveloperDataError(f"Developer-data file is missing: {normalized}")
        if target.stat().st_size != entry.size_bytes or sha256_file(target) != entry.sha256:
            raise DeveloperDataError(f"Developer-data file checksum mismatch: {normalized}")

    actual_paths = {
        path.relative_to(extraction_root).as_posix()
        for path in extraction_root.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }
    if actual_paths != expected_paths:
        unexpected = sorted(actual_paths.symmetric_difference(expected_paths))
        raise DeveloperDataError(f"Developer-data archive file list differs from its manifest: {unexpected}")
    try:
        payload = DeveloperDataPayload.model_validate_json(data_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DeveloperDataError("Developer-data payload is invalid.") from exc
    return manifest, payload


def _validate_archive_member(value: str) -> str:
    return _validate_relative_path(value)


def _validate_relative_path(value: str) -> str:
    if not value or "\\" in value:
        raise DeveloperDataError(f"Unsafe developer-data archive path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise DeveloperDataError(f"Unsafe developer-data archive path: {value!r}")
    return path.as_posix()
