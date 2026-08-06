from __future__ import annotations

from pathlib import Path

from card_reader_core.models import CardVersion, CardVersionImage, active_card_lifecycle_q, now_utc
from card_reader_core.storage import relativize_storage_path, resolve_storage_path, store_image

from .types import CardImageSource

_MAX_PUBLIC_IMAGE_CANDIDATE_LIMIT = 16
_PUBLIC_IMAGE_SCAN_LIMIT = 64


def resolve_image_file_path(image: CardVersionImage) -> Path | None:
    stored_path = resolve_storage_path(image.stored_path)
    if stored_path.exists():
        return stored_path

    source_path = resolve_storage_path(image.source_file)
    if source_path.exists():
        return source_path

    return None


def list_latest_active_card_image_sources(
    *,
    limit: int,
    card_ids: list[str] | None = None,
) -> list[CardImageSource]:
    normalized_limit = max(0, min(limit, _MAX_PUBLIC_IMAGE_CANDIDATE_LIMIT))
    if normalized_limit == 0:
        return []

    images = CardVersionImage.objects.filter(
        card_version__is_latest=True,
    ).filter(
        active_card_lifecycle_q(field_path="card_version__card__lifecycle_status")
    )
    if card_ids is not None:
        images = images.filter(card_version__card_id__in=card_ids)
    images = images.select_related("card_version__card").order_by(
        "card_version__card_id",
        "-created_at",
        "-id",
    )[:_PUBLIC_IMAGE_SCAN_LIMIT]

    sources: list[CardImageSource] = []
    seen_card_ids: set[str] = set()
    seen_checksums: set[str] = set()
    for image in images:
        card_id = str(image.card_version.card.id)
        if card_id in seen_card_ids:
            continue
        image_path = resolve_image_file_path(image)
        if image_path is None:
            continue
        seen_card_ids.add(card_id)
        checksum = image.checksum.strip()
        if not checksum or checksum in seen_checksums:
            continue
        seen_checksums.add(checksum)
        sources.append(
            CardImageSource(
                card_id=card_id,
                card_version_id=str(image.card_version.id),
                checksum=checksum,
                path=image_path,
            )
        )
        if len(sources) == normalized_limit:
            break
    return sources


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
