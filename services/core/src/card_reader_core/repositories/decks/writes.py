from __future__ import annotations

from uuid import UUID

from django.db import transaction

from card_reader_core.models import (
    Card,
    Deck,
    DeckCreation,
    DeckDifficulty,
    DeckEntry,
    DeckSideboard,
    DeckSideboardEntry,
    DeckVisibility,
    now_utc,
)


def create_deck(
    *,
    owner_id: str,
    name: str,
    description_markup: str | None,
    description: str | None,
    long_description_markup: str | None,
    long_description: str | None,
    difficulty: DeckDifficulty | None,
    visibility: DeckVisibility,
    hero_card: Card,
    client_creation_id: UUID | None = None,
) -> Deck:
    return Deck.objects.create(
        owner_id=owner_id,
        name=name,
        description_markup=description_markup,
        description=description,
        long_description_markup=long_description_markup,
        long_description=long_description,
        difficulty=difficulty,
        visibility=visibility,
        hero_card=hero_card,
        client_creation_id=client_creation_id,
    )


def create_deck_creation(
    *,
    owner_id: str,
    client_creation_id: UUID,
    deck: Deck,
) -> DeckCreation:
    return DeckCreation.objects.create(
        owner_id=owner_id,
        client_creation_id=client_creation_id,
        deck=deck,
    )


def update_deck(*, deck_id: str, updates: dict[str, object]) -> Deck | None:
    deck = Deck.objects.filter(id=deck_id).first()
    if deck is None:
        return None
    for field_name, field_value in updates.items():
        setattr(deck, field_name, field_value)
    deck.updated_at = now_utc()
    deck.save(update_fields=[*updates.keys(), "updated_at"])
    return deck


def delete_deck(*, deck_id: str, owner_id: str) -> bool:
    deleted, _ = Deck.objects.filter(id=deck_id, owner_id=owner_id).delete()
    return deleted > 0


@transaction.atomic
def replace_mainboard_entries(*, deck: Deck, entries: list[tuple[str, int]]) -> None:
    DeckEntry.objects.filter(deck=deck).delete()
    DeckEntry.objects.bulk_create(
        [
            DeckEntry(deck=deck, card_id=card_id, quantity=quantity, position=index)
            for index, (card_id, quantity) in enumerate(entries, start=1)
        ]
    )


@transaction.atomic
def replace_sideboards(*, deck: Deck, sideboards: list[dict[str, object]]) -> None:
    existing_by_id = {
        sideboard.id: sideboard
        for sideboard in DeckSideboard.objects.filter(deck=deck)
    }
    retained_sideboard_ids: set[str] = set()
    for sideboard in sideboards:
        source_id = sideboard.get("source_id")
        persisted_sideboard = (
            existing_by_id.get(str(source_id)) if source_id is not None else None
        )
        if persisted_sideboard is None:
            persisted_sideboard = DeckSideboard.objects.create(
                deck=deck,
                name=str(sideboard["name"]),
            )
        else:
            persisted_sideboard.name = str(sideboard["name"])
            persisted_sideboard.updated_at = now_utc()
            persisted_sideboard.save(update_fields=["name", "updated_at"])
            persisted_sideboard.entries.all().delete()
        retained_sideboard_ids.add(persisted_sideboard.id)
        entries = sideboard["entries"]
        if not isinstance(entries, list) or len(entries) == 0:
            continue
        DeckSideboardEntry.objects.bulk_create(
            [
                DeckSideboardEntry(
                    sideboard=persisted_sideboard,
                    card_id=str(card_id),
                    quantity=int(quantity),
                    position=index,
                )
                for index, (card_id, quantity) in enumerate(entries, start=1)
            ]
        )
    DeckSideboard.objects.filter(deck=deck).exclude(id__in=retained_sideboard_ids).delete()
