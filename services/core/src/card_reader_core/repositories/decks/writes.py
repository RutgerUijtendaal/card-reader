from __future__ import annotations

from django.db import transaction

from card_reader_core.models import Card, Deck, DeckEntry, DeckSideboard, DeckSideboardEntry, DeckVisibility, now_utc


def create_deck(*, owner_id: str, name: str, description: str | None, visibility: DeckVisibility, hero_card: Card) -> Deck:
    return Deck.objects.create(
        owner_id=owner_id,
        name=name,
        description=description,
        visibility=visibility,
        hero_card=hero_card,
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
    DeckSideboard.objects.filter(deck=deck).delete()
    for sideboard in sideboards:
        created_sideboard = DeckSideboard.objects.create(
            deck=deck,
            name=str(sideboard["name"]),
        )
        entries = sideboard["entries"]
        if not isinstance(entries, list) or len(entries) == 0:
            continue
        DeckSideboardEntry.objects.bulk_create(
            [
                DeckSideboardEntry(
                    sideboard=created_sideboard,
                    card_id=str(card_id),
                    quantity=int(quantity),
                    position=index,
                )
                for index, (card_id, quantity) in enumerate(entries, start=1)
            ]
        )
