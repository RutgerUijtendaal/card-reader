from __future__ import annotations

from pathlib import Path

from card_reader_core.models import CardVersionImage
from card_reader_core.repositories.cards.images import resolve_image_file_path
from card_reader_core.settings import settings
from card_reader_core.storage import resolve_storage_path
from card_reader_core.storage import relativize_image_storage_path


def card_image_asset_url(image: CardVersionImage | None, *, fallback_url: str | None = None) -> str | None:
    if image is None:
        return None

    stored_path = resolve_storage_path(image.stored_path)
    resolved_path = resolve_image_file_path(image)
    if resolved_path is None:
        return None
    if resolved_path is not None and resolved_path != stored_path:
        return fallback_url

    relative_path = _normalized_image_storage_path(image.stored_path)
    if relative_path is None:
        return fallback_url
    return f"/card-images/{relative_path}"


def _normalized_image_storage_path(storage_path: str) -> str | None:
    try:
        relative_path = relativize_image_storage_path(storage_path)
    except Exception:
        return None

    normalized = Path(relative_path).as_posix().strip("/")
    if not normalized.startswith("images/"):
        return None

    candidate = (settings.storage_root_dir.resolve() / normalized).resolve()
    images_root = (settings.storage_root_dir.resolve() / "images").resolve()
    try:
        candidate.relative_to(images_root)
    except ValueError:
        return None
    return normalized
