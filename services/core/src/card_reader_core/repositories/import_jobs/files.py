from __future__ import annotations

from pathlib import Path

from card_reader_core.storage import resolve_storage_path

from .types import SUPPORTED_IMAGE_SUFFIXES


def collect_supported_files(source_path: Path) -> list[Path]:
    source_path = resolve_storage_path(source_path)
    if source_path.is_file():
        return [source_path] if source_path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES else []
    if not source_path.is_dir():
        return []
    return sorted(
        path
        for path in source_path.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
    )
