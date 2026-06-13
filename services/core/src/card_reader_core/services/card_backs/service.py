from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from card_reader_core.models import CardBack
from card_reader_core.repositories.card_backs import (
    activate_card_back,
    create_card_back_record,
    get_card_back,
    get_current_card_back,
    list_card_backs,
)
from card_reader_core.storage import (
    build_storage_relative_path,
    calculate_checksum,
    relativize_image_storage_path,
    relativize_storage_path,
    resolve_storage_path,
    store_image,
)

ALLOWED_CARD_BACK_UPLOAD_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


class CardBackService:
    def list_history(self) -> list[CardBack]:
        return list_card_backs()

    def get_current(self) -> CardBack | None:
        return get_current_card_back()

    def activate(self, card_back_id: str) -> CardBack | None:
        card_back = get_card_back(card_back_id)
        if card_back is None:
            return None
        if not _stored_image_exists(card_back):
            raise ValueError("Card back image file is missing.")
        return activate_card_back(card_back_id)

    def upload(
        self,
        *,
        filename: str,
        chunks: Iterable[bytes],
        label: str | None = None,
    ) -> CardBack:
        original_filename = Path(filename).name
        suffix = Path(original_filename).suffix.lower()
        if suffix not in ALLOWED_CARD_BACK_UPLOAD_SUFFIXES:
            raise ValueError("Unsupported card-back file type. Use png/jpg/jpeg/webp/bmp/tif/tiff.")

        source_file = self._save_source_upload(original_filename=original_filename, suffix=suffix, chunks=chunks)
        source_path = resolve_storage_path(source_file)
        if source_path.stat().st_size == 0:
            source_path.unlink(missing_ok=True)
            raise ValueError("Uploaded file is empty.")

        try:
            width, height = _read_image_dimensions(source_path)
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            source_path.unlink(missing_ok=True)
            raise ValueError("Uploaded file must be a readable image.") from exc

        checksum = calculate_checksum(source_path)
        try:
            stored_path = store_image(source_path, checksum)
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            source_path.unlink(missing_ok=True)
            raise ValueError("Uploaded file must be a readable image.") from exc
        card_back = create_card_back_record(
            label=_normalize_label(label, original_filename),
            original_filename=original_filename,
            source_file=relativize_storage_path(source_file, default_root="uploads"),
            stored_path=stored_path,
            width=width,
            height=height,
            checksum=checksum,
        )
        activated = activate_card_back(card_back.id)
        if activated is None:
            raise ValueError("Uploaded card back could not be activated.")
        return activated

    def _save_source_upload(
        self,
        *,
        original_filename: str,
        suffix: str,
        chunks: Iterable[bytes],
    ) -> str:
        safe_stem = _safe_file_stem(original_filename, fallback="card-back")
        relative_path = build_storage_relative_path(
            "uploads",
            "card-backs",
            f"{safe_stem}-{uuid4().hex[:8]}{suffix}",
        )
        target_path = resolve_storage_path(relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open("wb") as stream:
            for chunk in chunks:
                stream.write(chunk)
        return relative_path


def _read_image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        dimensions = (image.width, image.height)
        image.verify()
        return dimensions


def _safe_file_stem(filename: str, *, fallback: str) -> str:
    stem = Path(filename).stem.strip().lower()
    return re.sub(r"[^a-z0-9_-]+", "-", stem).strip("-") or fallback


def _normalize_label(label: str | None, filename: str) -> str:
    normalized = (label or "").strip()
    if normalized:
        return normalized
    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    return stem or "Card Back"


def _stored_image_exists(card_back: CardBack) -> bool:
    try:
        relative_path = relativize_image_storage_path(card_back.stored_path)
    except Exception:
        return False
    normalized = Path(relative_path).as_posix().strip("/")
    if not normalized.startswith("images/"):
        return False
    path = resolve_storage_path(normalized)
    return path.exists() and path.is_file()
