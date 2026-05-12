from __future__ import annotations

import hashlib
import shutil
from pathlib import Path, PurePosixPath

from .settings import settings

_KNOWN_STORAGE_ROOTS = ("images", "uploads", "symbols", "debug-crops", "maintenance", "logs")


def calculate_checksum(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with file_path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_storage_relative_path(*parts: str | Path) -> str:
    normalized_parts = [str(part).replace("\\", "/").strip("/") for part in parts if str(part).strip("/\\")]
    return PurePosixPath(*normalized_parts).as_posix()


def build_image_storage_path(source_file: Path, checksum: str) -> str:
    return build_storage_relative_path("images", f"{checksum}{source_file.suffix.lower()}")


def resolve_storage_path(storage_path: str | Path) -> Path:
    raw_path = str(storage_path)
    if _looks_absolute_path(raw_path):
        return Path(raw_path)
    normalized_path = _normalize_relative_storage_path(raw_path)
    return settings.storage_root_dir / Path(normalized_path)


def relativize_storage_path(
    storage_path: str | Path,
    *,
    allowed_roots: tuple[str, ...] = _KNOWN_STORAGE_ROOTS,
    default_root: str | None = None,
) -> str:
    raw_path = str(storage_path)
    if not _looks_absolute_path(raw_path):
        return _normalize_relative_storage_path(raw_path)

    try:
        return Path(raw_path).relative_to(settings.storage_root_dir).as_posix()
    except ValueError:
        pass

    normalized = raw_path.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part and part != "."]
    indexes = [index for index, part in enumerate(parts) if part.lower() in {root.lower() for root in allowed_roots}]
    if indexes:
        return PurePosixPath(*parts[indexes[-1] :]).as_posix()
    if default_root is not None and parts:
        return PurePosixPath(default_root, parts[-1]).as_posix()
    return PurePosixPath(*parts).as_posix()


def relativize_image_storage_path(storage_path: str | Path) -> str:
    return relativize_storage_path(storage_path, allowed_roots=("images",), default_root="images")


def store_image(source_file: Path, checksum: str) -> str:
    relative_path = build_image_storage_path(source_file, checksum)
    target_path = resolve_storage_path(relative_path)
    if not target_path.exists():
        shutil.copy2(source_file, target_path)
    return relative_path


def _looks_absolute_path(value: str) -> bool:
    if not value:
        return False
    if value.startswith(("/", "\\")):
        return True
    return len(value) >= 3 and value[1] == ":" and value[2] in {"\\", "/"}


def _normalize_relative_storage_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part and part != "."]
    return PurePosixPath(*parts).as_posix()

