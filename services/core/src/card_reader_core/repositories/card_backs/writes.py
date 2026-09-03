from __future__ import annotations

from django.db import transaction

from card_reader_core.models import (
    CardBack,
    CardBackFactionDefault,
    CardBackPoolDefault,
    CardFaction,
    CardPool,
    now_utc,
)


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
        updated_at=now_utc(),
    )


def upsert_pool_default(*, card_pool: CardPool, card_back: CardBack) -> CardBackPoolDefault:
    with transaction.atomic():
        row, _created = CardBackPoolDefault.objects.update_or_create(
            card_pool=card_pool,
            defaults={"card_back": card_back, "updated_at": now_utc()},
        )
        return row


def delete_pool_default(*, card_pool: CardPool) -> None:
    CardBackPoolDefault.objects.filter(card_pool=card_pool).delete()


def upsert_faction_default(
    *,
    faction: CardFaction,
    card_back: CardBack,
) -> CardBackFactionDefault:
    with transaction.atomic():
        row, _created = CardBackFactionDefault.objects.update_or_create(
            faction=faction,
            defaults={"card_back": card_back, "updated_at": now_utc()},
        )
        return row


def delete_faction_default(*, faction: CardFaction) -> None:
    CardBackFactionDefault.objects.filter(faction=faction).delete()
