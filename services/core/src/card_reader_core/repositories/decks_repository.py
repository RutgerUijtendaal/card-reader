from __future__ import annotations

from django.db import transaction
from django.db.models import Prefetch, Q, QuerySet

from card_reader_core.models import (
    Card,
    CardVersionKeyword,
    CardVersionSymbol,
    CardVersionTag,
    CardVersionType,
    Deck,
    DeckEntry,
    DeckSideboard,
    DeckSideboardEntry,
    DeckVisibility,
    now_utc,
)


PUBLIC_DECK_VISIBILITIES: tuple[DeckVisibility, DeckVisibility] = ("public", "unlisted")


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


def list_public_decks(
    *,
    hero_query: str | None = None,
    card_query: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
) -> list[Deck]:
    return list(
        _apply_public_deck_filters(
            _deck_queryset().filter(visibility="public"),
            hero_query=hero_query,
            card_query=card_query,
            affinity_symbol_ids=affinity_symbol_ids,
            affinity_symbol_match=affinity_symbol_match,
        ).order_by("-updated_at", "-created_at")
    )


def list_owner_decks(owner_id: str) -> list[Deck]:
    return list(_deck_queryset().filter(owner_id=owner_id).order_by("-updated_at", "-created_at"))


def get_public_deck(deck_id: str) -> Deck | None:
    return _deck_queryset().filter(id=deck_id, visibility="public").first()


def get_owner_deck(deck_id: str, owner_id: str) -> Deck | None:
    return _deck_queryset().filter(id=deck_id, owner_id=owner_id).first()


def get_deck_for_viewer(deck_id: str, *, viewer_id: str | None = None) -> Deck | None:
    query = _deck_queryset().filter(id=deck_id)
    if viewer_id:
        return query.filter(visibility__in=PUBLIC_DECK_VISIBILITIES).first() or query.filter(owner_id=viewer_id).first()
    return query.filter(visibility__in=PUBLIC_DECK_VISIBILITIES).first()


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
            DeckEntry(deck=deck, card_id=card_id, quantity=quantity)
            for card_id, quantity in entries
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
                )
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
        ),
        Prefetch(
            "sideboards",
            queryset=DeckSideboard.objects.prefetch_related(
                Prefetch(
                    "entries",
                    queryset=DeckSideboardEntry.objects.select_related(
                        "card",
                        "card__latest_version",
                        "card__latest_version__template",
                        "card__latest_version__previous_version",
                    )
                    .prefetch_related(*_latest_version_metadata_prefetches("card__latest_version"))
                    .order_by("card__label", "created_at"),
                )
            ).order_by("created_at", "id"),
        ),
    )


def _apply_public_deck_filters(
    queryset: QuerySet[Deck],
    *,
    hero_query: str | None,
    card_query: str | None,
    affinity_symbol_ids: list[str] | None,
    affinity_symbol_match: str | None,
) -> QuerySet[Deck]:
    filtered = queryset

    normalized_hero_query = (hero_query or "").strip()
    if normalized_hero_query:
        filtered = filtered.filter(
            Q(hero_card__label__icontains=normalized_hero_query)
            | Q(hero_card__latest_version__name__icontains=normalized_hero_query)
        )

    normalized_card_query = (card_query or "").strip()
    if normalized_card_query:
        filtered = filtered.filter(
            Q(entries__card__label__icontains=normalized_card_query)
            | Q(entries__card__latest_version__name__icontains=normalized_card_query)
            | Q(sideboards__entries__card__label__icontains=normalized_card_query)
            | Q(sideboards__entries__card__latest_version__name__icontains=normalized_card_query)
        )

    normalized_affinity_symbol_ids = [symbol_id.strip() for symbol_id in affinity_symbol_ids or [] if symbol_id.strip()]
    if normalized_affinity_symbol_ids:
        match_all = affinity_symbol_match == "all"
        if match_all:
            for symbol_id in normalized_affinity_symbol_ids:
                filtered = filtered.filter(_affinity_symbol_query(symbol_id))
        else:
            affinity_query = Q()
            for symbol_id in normalized_affinity_symbol_ids:
                affinity_query |= _affinity_symbol_query(symbol_id)
            filtered = filtered.filter(affinity_query)

    return filtered.distinct()


def _affinity_symbol_query(symbol_id: str) -> Q:
    return (
        Q(
            hero_card__latest_version__card_version_symbols__symbol_id=symbol_id,
            hero_card__latest_version__card_version_symbols__symbol__symbol_type="affinity",
        )
        | Q(
            entries__card__latest_version__card_version_symbols__symbol_id=symbol_id,
            entries__card__latest_version__card_version_symbols__symbol__symbol_type="affinity",
        )
        | Q(
            sideboards__entries__card__latest_version__card_version_symbols__symbol_id=symbol_id,
            sideboards__entries__card__latest_version__card_version_symbols__symbol__symbol_type="affinity",
        )
    )


def _latest_version_metadata_prefetches(prefix: str) -> tuple[Prefetch[str], ...]:
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
