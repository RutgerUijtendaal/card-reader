from __future__ import annotations

from collections.abc import Iterable

from django.db import transaction

from card_reader_core.metadata import MANA_FAMILY_BY_KEY, ManaFamily, normalize_mana_family_keys
from card_reader_core.models import (
    Card,
    CardManaFamilyAssignment,
    card_mana_family_sort_key,
    now_utc,
)


@transaction.atomic
def set_card_mana_families(
    *,
    card: Card,
    mana_families: Iterable[str],
) -> tuple[ManaFamily, ...]:
    requested = tuple(value.strip().casefold() for value in mana_families)
    if any(value not in MANA_FAMILY_BY_KEY for value in requested):
        raise ValueError("Invalid card mana family.")
    normalized = normalize_mana_family_keys(requested)
    locked_card = Card.objects.select_for_update().get(pk=card.pk)

    CardManaFamilyAssignment.objects.filter(card_id=locked_card.id).exclude(
        mana_family__in=normalized
    ).delete()
    existing = set(
        CardManaFamilyAssignment.objects.filter(card_id=locked_card.id).values_list(
            "mana_family", flat=True
        )
    )
    CardManaFamilyAssignment.objects.bulk_create(
        [
            CardManaFamilyAssignment(card=locked_card, mana_family=mana_family)
            for mana_family in normalized
            if mana_family not in existing
        ],
        ignore_conflicts=True,
    )

    sort_key = card_mana_family_sort_key(normalized)
    if locked_card.mana_family_sort_key != sort_key:
        locked_card.mana_family_sort_key = sort_key
        locked_card.updated_at = now_utc()
        locked_card.save(update_fields=["mana_family_sort_key", "updated_at"])
        card.mana_family_sort_key = sort_key
        card.updated_at = locked_card.updated_at
    prefetched = getattr(card, "_prefetched_objects_cache", None)
    if prefetched is not None:
        prefetched.pop("mana_family_assignments", None)
    return normalized
