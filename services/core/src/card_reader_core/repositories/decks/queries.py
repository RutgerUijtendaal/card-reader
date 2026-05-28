from __future__ import annotations

from card_reader_core.models import Deck, DeckVisibility

from .filters import apply_public_deck_filters
from .prefetch import deck_queryset

PUBLIC_DECK_VISIBILITIES: tuple[DeckVisibility, DeckVisibility] = ("public", "unlisted")


def list_public_decks(
    *,
    hero_query: str | None = None,
    card_query: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_exclude_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
) -> list[Deck]:
    return list(
        apply_public_deck_filters(
            deck_queryset().filter(visibility="public"),
            hero_query=hero_query,
            card_query=card_query,
            affinity_symbol_ids=affinity_symbol_ids,
            affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
            affinity_symbol_match=affinity_symbol_match,
        ).order_by("-updated_at", "-created_at")
    )


def list_owner_decks(owner_id: str) -> list[Deck]:
    return list(deck_queryset().filter(owner_id=owner_id).order_by("-updated_at", "-created_at"))


def get_public_deck(deck_id: str) -> Deck | None:
    return deck_queryset().filter(id=deck_id, visibility="public").first()


def get_owner_deck(deck_id: str, owner_id: str) -> Deck | None:
    return deck_queryset().filter(id=deck_id, owner_id=owner_id).first()


def get_deck_for_viewer(deck_id: str, *, viewer_id: str | None = None) -> Deck | None:
    query = deck_queryset().filter(id=deck_id)
    if viewer_id:
        return query.filter(visibility__in=PUBLIC_DECK_VISIBILITIES).first() or query.filter(owner_id=viewer_id).first()
    return query.filter(visibility__in=PUBLIC_DECK_VISIBILITIES).first()
