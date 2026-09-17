from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from card_reader_core.models import CardBack
from card_reader_core.repositories.card_backs import create_card_back_record, list_card_backs
from card_reader_core.storage import (
    build_storage_relative_path,
    calculate_checksum,
    relativize_image_storage_path,
    relativize_storage_path,
    resolve_storage_path,
    store_image,
)

ALLOWED_CARD_BACK_UPLOAD_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreparedCardBack:
    label: str
    original_filename: str
    source_file: str
    stored_path: str
    width: int
    height: int
    checksum: str


def discard_card_back_source(source_file: str) -> None:
    """Best-effort cleanup; content-addressed images may be shared and are retained."""
    try:
        resolve_storage_path(source_file).unlink(missing_ok=True)
    except OSError:
        logger.exception("Could not clean up card-back upload")


def create_prepared_card_back(prepared: PreparedCardBack) -> CardBack:
    return create_card_back_record(
        label=prepared.label,
        original_filename=prepared.original_filename,
        source_file=prepared.source_file,
        stored_path=prepared.stored_path,
        width=prepared.width,
        height=prepared.height,
        checksum=prepared.checksum,
    )


def list_card_back_assets() -> list[CardBack]:
    return list_card_backs()


def upload_card_back_asset(
    *,
    filename: str,
    chunks: Iterable[bytes],
    label: str | None = None,
) -> CardBack:
    prepared = prepare_card_back_asset(filename=filename, chunks=chunks, label=label)
    try:
        return create_prepared_card_back(prepared)
    except Exception:
        discard_card_back_source(prepared.source_file)
        raise


def prepare_card_back_asset(
    *,
    filename: str,
    chunks: Iterable[bytes],
    label: str | None = None,
) -> PreparedCardBack:
    original_filename = Path(filename).name
    suffix = Path(original_filename).suffix.lower()
    if suffix not in ALLOWED_CARD_BACK_UPLOAD_SUFFIXES:
        raise ValueError("Unsupported card-back file type. Use png/jpg/jpeg/webp/bmp/tif/tiff.")

    source_file = _save_source_upload(
        original_filename=original_filename,
        suffix=suffix,
        chunks=chunks,
    )
    source_path = resolve_storage_path(source_file)
    if source_path.stat().st_size == 0:
        discard_card_back_source(source_file)
        raise ValueError("Uploaded file is empty.")

    try:
        width, height = _read_image_dimensions(source_path)
        checksum = calculate_checksum(source_path)
        stored_path = store_image(source_path, checksum)
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        discard_card_back_source(source_file)
        raise ValueError("Uploaded file must be a readable image.") from exc

    return PreparedCardBack(
        label=_normalize_label(label, original_filename),
        original_filename=original_filename,
        source_file=relativize_storage_path(source_file, default_root="uploads"),
        stored_path=stored_path,
        width=width,
        height=height,
        checksum=checksum,
    )


def resolve_card_back_image_asset_path(card_back: CardBack) -> str | None:
    try:
        relative_path = relativize_image_storage_path(card_back.stored_path)
    except Exception:
        return None
    normalized = Path(relative_path).as_posix().strip("/")
    if not normalized.startswith("images/"):
        return None
    path = resolve_storage_path(normalized).resolve()
    images_root = resolve_storage_path("images").resolve()
    try:
        path.relative_to(images_root)
    except ValueError:
        return None
    if not path.exists() or not path.is_file():
        return None
    return normalized


def _save_source_upload(*, original_filename: str, suffix: str, chunks: Iterable[bytes]) -> str:
    safe_stem = _safe_file_stem(original_filename, fallback="card-back")
    relative_path = build_storage_relative_path(
        "uploads",
        "card-backs",
        f"{safe_stem}-{uuid4().hex[:8]}{suffix}",
    )
    target_path = resolve_storage_path(relative_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target_path.open("wb") as stream:
            for chunk in chunks:
                stream.write(chunk)
    except Exception:
        discard_card_back_source(relative_path)
        raise
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
