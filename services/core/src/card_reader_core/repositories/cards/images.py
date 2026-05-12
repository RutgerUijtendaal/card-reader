from __future__ import annotations

from pathlib import Path

from card_reader_core.models import CardVersion, CardVersionImage, now_utc
from card_reader_core.storage import relativize_storage_path, resolve_storage_path, store_image


def resolve_image_file_path(image: CardVersionImage) -> Path | None:
    stored_path = resolve_storage_path(image.stored_path)
    if stored_path.exists():
        return stored_path

    source_path = resolve_storage_path(image.source_file)
    if source_path.exists():
        return source_path

    return None


def save_image_record(version: CardVersion, source_file: str, checksum: str) -> None:
    resolved_source_file = resolve_storage_path(source_file)
    stored_path = store_image(resolved_source_file, checksum)
    CardVersionImage.objects.create(
        card_version=version,
        source_file=relativize_storage_path(
            source_file,
            default_root="uploads",
            preserve_unmatched_absolute=True,
        ),
        stored_path=stored_path,
        checksum=checksum,
        updated_at=now_utc(),
    )
