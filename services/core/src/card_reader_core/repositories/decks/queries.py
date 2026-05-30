from __future__ import annotations

from django.db.models import Q

from card_reader_core.models import Deck, DeckVisibility

from .filters import apply_deck_filters
from .prefetch import deck_queryset

PUBLIC_DECK_VISIBILITIES: tuple[DeckVisibility, DeckVisibility] = ("public", "unlisted")


def list_public_decks(
    *,
    hero_query: str | None = None,
    author_query: str | None = None,
    card_query: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_exclude_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
) -> list[Deck]:
    return list(
        apply_deck_filters(
            deck_queryset().filter(visibility="public"),
            hero_query=hero_query,
            author_query=author_query,
            card_query=card_query,
            affinity_symbol_ids=affinity_symbol_ids,
            affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
            affinity_symbol_match=affinity_symbol_match,
        ).order_by("-updated_at", "-created_at")
    )


def list_owner_decks(
    owner_id: str,
    *,
    hero_query: str | None = None,
    card_query: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_exclude_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
) -> list[Deck]:
    return list(
        apply_deck_filters(
            deck_queryset().filter(owner_id=owner_id),
            hero_query=hero_query,
            author_query=None,
            card_query=card_query,
            affinity_symbol_ids=affinity_symbol_ids,
            affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
            affinity_symbol_match=affinity_symbol_match,
        ).order_by("-updated_at", "-created_at")
    )


def list_card_decks_for_viewer(card_id: str, *, viewer_id: str | None = None) -> list[Deck]:
    visibility_query = Q(visibility="public")
    if viewer_id:
        visibility_query |= Q(owner_id=viewer_id)
    return list(
        deck_queryset()
        .filter(
            visibility_query,
            Q(hero_card_id=card_id) | Q(entries__card_id=card_id) | Q(sideboards__entries__card_id=card_id),
        )
        .distinct()
        .order_by("-updated_at", "-created_at", "id")
    )


def get_public_deck(deck_id: str) -> Deck | None:
    return deck_queryset().filter(id=deck_id, visibility="public").first()


def get_owner_deck(deck_id: str, owner_id: str) -> Deck | None:
    return deck_queryset().filter(id=deck_id, owner_id=owner_id).first()


def get_deck_for_viewer(deck_id: str, *, viewer_id: str | None = None) -> Deck | None:
    query = deck_queryset().filter(id=deck_id)
    if viewer_id:
        return query.filter(visibility__in=PUBLIC_DECK_VISIBILITIES).first() or query.filter(owner_id=viewer_id).first()
    return query.filter(visibility__in=PUBLIC_DECK_VISIBILITIES).first()
