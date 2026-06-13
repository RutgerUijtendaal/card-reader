from __future__ import annotations

from django.db import transaction

from card_reader_core.models import CardBack, now_utc


def create_card_back_record(
    *,
    label: str,
    original_filename: str,
    source_file: str,
    stored_path: str,
    width: int,
    height: int,
    checksum: str,
) -> CardBack:
    return CardBack.objects.create(
        label=label,
        original_filename=original_filename,
        source_file=source_file,
        stored_path=stored_path,
        width=width,
        height=height,
        checksum=checksum,
        is_current=False,
        updated_at=now_utc(),
    )


def activate_card_back(card_back_id: str) -> CardBack | None:
    with transaction.atomic():
        target = CardBack.objects.select_for_update().filter(id=card_back_id).first()
        if target is None:
            return None

        timestamp = now_utc()
        CardBack.objects.filter(is_current=True).exclude(id=target.id).update(
            is_current=False,
            updated_at=timestamp,
        )
        if not target.is_current:
            target.is_current = True
            target.updated_at = timestamp
            target.save(update_fields=["is_current", "updated_at"])
        return target
