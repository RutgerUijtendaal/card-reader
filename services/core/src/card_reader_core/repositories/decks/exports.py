from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from card_reader_core.models import (
    Card,
    Deck,
    DeckEntry,
    DeckSideboard,
    DeckSideboardEntry,
    DeckTagAssignment,
)

DeckExportRole = Literal["hero", "mainboard", "sideboard"]


@dataclass(frozen=True)
class DeckExportEntrySnapshot:
    card_id: str
    card_name: str
    quantity: int
    role: DeckExportRole
    required: bool


@dataclass(frozen=True)
class DeckExportTagSnapshot:
    id: str
    key: str
    label: str
    kind: str


@dataclass(frozen=True)
class DeckExportSnapshot:
    deck_id: str
    collection_name: str
    collection_description: str | None
    scope: Literal["mainboard", "sideboard"]
    hero_card_id: str
    difficulty: str | None
    entries: list[DeckExportEntrySnapshot]
    tags: list[DeckExportTagSnapshot]
    sideboard_id: str | None = None
    sideboard_name: str | None = None


def get_deck_export_snapshot(
    deck_id: str,
    *,
    sideboard_id: str | None = None,
) -> DeckExportSnapshot | None:
    deck = (
        Deck.objects.select_related("hero_card", "hero_card__latest_version")
        .filter(id=deck_id)
        .first()
    )
    if deck is None:
        return None

    tags = [
        DeckExportTagSnapshot(
            id=assignment.tag.id,
            key=assignment.tag.key,
            label=assignment.tag.label,
            kind=assignment.tag.kind,
        )
        for assignment in DeckTagAssignment.objects.select_related("tag")
        .filter(deck_id=deck.id)
        .order_by("tag__kind", "tag__label", "id")
    ]

    if sideboard_id is None:
        entries = [
            DeckExportEntrySnapshot(
                card_id=deck.hero_card.id,
                card_name=_card_name(deck.hero_card),
                quantity=1,
                role="hero",
                required=True,
            ),
            *[
                DeckExportEntrySnapshot(
                    card_id=entry.card.id,
                    card_name=_card_name(entry.card),
                    quantity=int(entry.quantity),
                    role="mainboard",
                    required=False,
                )
                for entry in DeckEntry.objects.select_related("card", "card__latest_version")
                .filter(deck_id=deck.id)
                .order_by("position", "card_id")
            ],
        ]
        return DeckExportSnapshot(
            deck_id=deck.id,
            collection_name=deck.name,
            collection_description=deck.description,
            scope="mainboard",
            hero_card_id=deck.hero_card.id,
            difficulty=deck.difficulty,
            entries=entries,
            tags=tags,
        )

    sideboard = DeckSideboard.objects.filter(id=sideboard_id, deck_id=deck.id).first()
    if sideboard is None:
        return None
    entries = [
        DeckExportEntrySnapshot(
            card_id=entry.card.id,
            card_name=_card_name(entry.card),
            quantity=int(entry.quantity),
            role="sideboard",
            required=False,
        )
        for entry in DeckSideboardEntry.objects.select_related("card", "card__latest_version")
        .filter(sideboard_id=sideboard.id)
        .order_by("position", "card_id")
    ]
    return DeckExportSnapshot(
        deck_id=deck.id,
        collection_name=f"{deck.name} - {sideboard.name}",
        collection_description=deck.description,
        scope="sideboard",
        hero_card_id=deck.hero_card.id,
        difficulty=deck.difficulty,
        entries=entries,
        tags=tags,
        sideboard_id=sideboard.id,
        sideboard_name=sideboard.name,
    )


def _card_name(card: Card) -> str:
    return card.latest_version.name if card.latest_version is not None else card.label
