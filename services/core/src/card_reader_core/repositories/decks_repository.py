from __future__ import annotations

from django.db import transaction
from django.db.models import Prefetch, QuerySet

from card_reader_core.models import (
    Card,
    CardVersionKeyword,
    CardVersionSymbol,
    CardVersionTag,
    CardVersionType,
    Deck,
    DeckEntry,
    now_utc,
)


def get_cards_by_ids(card_ids: list[str]) -> dict[str, Card]:
    if not card_ids:
        return {}
    return {
        card.id: card
        for card in Card.objects.filter(id__in=card_ids).select_related(
            "latest_version",
            "latest_version__template",
            "latest_version__previous_version",
        ).prefetch_related(*_latest_version_metadata_prefetches("latest_version"))
    }


def get_deck_card(card_id: str) -> Card | None:
    return (
        Card.objects.filter(id=card_id)
        .select_related("latest_version", "latest_version__template", "latest_version__previous_version")
        .prefetch_related(*_latest_version_metadata_prefetches("latest_version"))
        .first()
    )


def list_public_decks() -> list[Deck]:
    return list(_deck_queryset().filter(is_public=True).order_by("-updated_at", "-created_at"))


def list_owner_decks(owner_id: str) -> list[Deck]:
    return list(_deck_queryset().filter(owner_id=owner_id).order_by("-updated_at", "-created_at"))


def get_public_deck(deck_id: str) -> Deck | None:
    return _deck_queryset().filter(id=deck_id, is_public=True).first()


def get_owner_deck(deck_id: str, owner_id: str) -> Deck | None:
    return _deck_queryset().filter(id=deck_id, owner_id=owner_id).first()


def get_deck_for_viewer(deck_id: str, *, viewer_id: str | None = None) -> Deck | None:
    query = _deck_queryset().filter(id=deck_id)
    if viewer_id:
        return query.filter(is_public=True).first() or query.filter(owner_id=viewer_id).first()
    return query.filter(is_public=True).first()


def create_deck(*, owner_id: str, name: str, description: str | None, is_public: bool, hero_card: Card) -> Deck:
    return Deck.objects.create(
        owner_id=owner_id,
        name=name,
        description=description,
        is_public=is_public,
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
def replace_deck_entries(*, deck: Deck, entries: list[tuple[str, int]]) -> None:
    DeckEntry.objects.filter(deck=deck).delete()
    DeckEntry.objects.bulk_create(
        [
            DeckEntry(deck=deck, card_id=card_id, quantity=quantity)
            for card_id, quantity in entries
        ]
    )


def _deck_queryset() -> QuerySet[Deck]:
    return Deck.objects.select_related(
        "owner",
        "hero_card",
        "hero_card__latest_version",
        "hero_card__latest_version__template",
        "hero_card__latest_version__previous_version",
    ).prefetch_related(
        *_latest_version_metadata_prefetches("hero_card__latest_version"),
        Prefetch(
            "entries",
            queryset=DeckEntry.objects.select_related(
                "card",
                "card__latest_version",
                "card__latest_version__template",
                "card__latest_version__previous_version",
            ).prefetch_related(*_latest_version_metadata_prefetches("card__latest_version")).order_by("card__label", "created_at"),
        )
    )


def _latest_version_metadata_prefetches(prefix: str) -> tuple[Prefetch, ...]:
    return (
        Prefetch(
            f"{prefix}__card_version_keywords",
            queryset=CardVersionKeyword.objects.select_related("keyword").order_by("keyword__label"),
        ),
        Prefetch(
            f"{prefix}__card_version_tags",
            queryset=CardVersionTag.objects.select_related("tag").order_by("tag__label"),
        ),
        Prefetch(
            f"{prefix}__card_version_symbols",
            queryset=CardVersionSymbol.objects.select_related("symbol").order_by("symbol__label"),
        ),
        Prefetch(
            f"{prefix}__card_version_types",
            queryset=CardVersionType.objects.select_related("type").order_by("type__label"),
        ),
    )
