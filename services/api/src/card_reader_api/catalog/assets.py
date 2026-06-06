from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from django.core.files.uploadedfile import UploadedFile

from card_reader_core.storage import build_storage_relative_path, resolve_storage_path

ALLOWED_SYMBOL_ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def store_symbol_asset(upload: UploadedFile, filename: str, suffix: str) -> Path:
    stem = Path(filename).stem.strip().lower()
    safe_stem = re.sub(r"[^a-z0-9_-]+", "-", stem).strip("-") or "symbol"
    relative_path = build_storage_relative_path("symbols", "uploads", f"{safe_stem}-{uuid4().hex[:8]}{suffix}")
    target_path = resolve_storage_path(relative_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("wb") as stream:
        for chunk in upload.chunks():
            stream.write(chunk)
    return target_path
