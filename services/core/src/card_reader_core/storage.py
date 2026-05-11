from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from .settings import settings


def calculate_checksum(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with file_path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def store_image(source_file: Path, checksum: str) -> Path:
    target_path = settings.image_store_dir / f"{checksum}{source_file.suffix.lower()}"
    if not target_path.exists():
        shutil.copy2(source_file, target_path)
    return target_path

