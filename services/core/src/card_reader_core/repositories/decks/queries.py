from __future__ import annotations

from datetime import datetime
from uuid import UUID

from django.db.models import Case, IntegerField, Q, QuerySet, Value, When
from django.utils import timezone

from card_reader_core.models import CardPoolScope, Deck, DeckCreation, DeckVisibility

from .filters import apply_deck_filters
from .prefetch import deck_queryset, deck_summary_queryset, deck_validation_queryset
from .types import DeckSummaryPage

PUBLIC_DECK_VISIBILITIES: tuple[DeckVisibility, DeckVisibility] = ("public", "unlisted")
PAGINATED_DECK_ORDERING = ("-created_at", "id")


def list_public_decks(
    *,
    card_pool_scope: CardPoolScope,
    search_query: str | None = None,
    hero_query: str | None = None,
    author_query: str | None = None,
    card_query: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_exclude_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
    deck_tag_ids: list[str] | None = None,
    deck_tag_exclude_ids: list[str] | None = None,
    deck_tag_match: str | None = None,
) -> list[Deck]:
    return list(
        apply_deck_filters(
            deck_queryset().filter(visibility="public"),
            search_query=search_query,
            hero_query=hero_query,
            author_query=author_query,
            card_query=card_query,
            affinity_symbol_ids=affinity_symbol_ids,
            affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
            affinity_symbol_match=affinity_symbol_match,
            deck_tag_ids=deck_tag_ids,
            deck_tag_exclude_ids=deck_tag_exclude_ids,
            deck_tag_match=deck_tag_match,
            card_pool_scope=card_pool_scope,
        ).order_by("-updated_at", "-created_at")
    )


def list_owner_decks(
    owner_id: str,
    *,
    search_query: str | None = None,
    hero_query: str | None = None,
    card_query: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_exclude_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
    deck_tag_ids: list[str] | None = None,
    deck_tag_exclude_ids: list[str] | None = None,
    deck_tag_match: str | None = None,
    card_pool_scope: CardPoolScope,
) -> list[Deck]:
    return list(
        apply_deck_filters(
            deck_queryset().filter(owner_id=owner_id),
            search_query=search_query,
            hero_query=hero_query,
            author_query=None,
            card_query=card_query,
            affinity_symbol_ids=affinity_symbol_ids,
            affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
            affinity_symbol_match=affinity_symbol_match,
            deck_tag_ids=deck_tag_ids,
            deck_tag_exclude_ids=deck_tag_exclude_ids,
            deck_tag_match=deck_tag_match,
            card_pool_scope=card_pool_scope,
        ).order_by("-updated_at", "-created_at")
    )


def list_public_deck_summaries(
    *,
    card_pool_scope: CardPoolScope,
    search_query: str | None = None,
    hero_query: str | None = None,
    author_query: str | None = None,
    card_query: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_exclude_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
    deck_tag_ids: list[str] | None = None,
    deck_tag_exclude_ids: list[str] | None = None,
    deck_tag_match: str | None = None,
) -> list[Deck]:
    return list(
        apply_deck_filters(
            deck_summary_queryset().filter(visibility="public"),
            search_query=search_query,
            hero_query=hero_query,
            author_query=author_query,
            card_query=card_query,
            affinity_symbol_ids=affinity_symbol_ids,
            affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
            affinity_symbol_match=affinity_symbol_match,
            deck_tag_ids=deck_tag_ids,
            deck_tag_exclude_ids=deck_tag_exclude_ids,
            deck_tag_match=deck_tag_match,
            card_pool_scope=card_pool_scope,
        ).order_by("-updated_at", "-created_at")
    )


def list_owner_deck_summaries(
    owner_id: str,
    *,
    search_query: str | None = None,
    hero_query: str | None = None,
    card_query: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_exclude_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
    deck_tag_ids: list[str] | None = None,
    deck_tag_exclude_ids: list[str] | None = None,
    deck_tag_match: str | None = None,
    card_pool_scope: CardPoolScope,
) -> list[Deck]:
    return list(
        apply_deck_filters(
            deck_summary_queryset().filter(owner_id=owner_id),
            search_query=search_query,
            hero_query=hero_query,
            author_query=None,
            card_query=card_query,
            affinity_symbol_ids=affinity_symbol_ids,
            affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
            affinity_symbol_match=affinity_symbol_match,
            deck_tag_ids=deck_tag_ids,
            deck_tag_exclude_ids=deck_tag_exclude_ids,
            deck_tag_match=deck_tag_match,
            card_pool_scope=card_pool_scope,
        ).order_by("-updated_at", "-created_at")
    )


def list_public_deck_summary_candidates(
    *,
    card_pool_scope: CardPoolScope,
    snapshot_at: datetime,
    search_query: str | None = None,
    hero_query: str | None = None,
    author_query: str | None = None,
    card_query: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_exclude_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
    deck_tag_ids: list[str] | None = None,
    deck_tag_exclude_ids: list[str] | None = None,
    deck_tag_match: str | None = None,
) -> list[Deck]:
    return list(
        apply_deck_filters(
            deck_validation_queryset().filter(
                visibility="public",
                created_at__lte=snapshot_at,
            ),
            search_query=search_query,
            hero_query=hero_query,
            author_query=author_query,
            card_query=card_query,
            affinity_symbol_ids=affinity_symbol_ids,
            affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
            affinity_symbol_match=affinity_symbol_match,
            deck_tag_ids=deck_tag_ids,
            deck_tag_exclude_ids=deck_tag_exclude_ids,
            deck_tag_match=deck_tag_match,
            card_pool_scope=card_pool_scope,
        ).order_by(*PAGINATED_DECK_ORDERING)
    )


def get_public_deck_summary_page_by_candidates(
    ordered_decks: list[Deck],
    *,
    page: int,
    page_size: int,
    snapshot_at: datetime,
    cursor_created_at: datetime | None = None,
    cursor_id: str | None = None,
) -> DeckSummaryPage:
    count = len(ordered_decks)
    normalized_page, normalized_page_size, offset = _pagination_bounds(
        count=count,
        page=page,
        page_size=page_size,
    )
    remaining_decks = _decks_after_cursor(
        ordered_decks,
        cursor_created_at=cursor_created_at,
        cursor_id=cursor_id,
    )
    page_offset = 0 if cursor_created_at is not None and cursor_id is not None else offset
    page_candidates = remaining_decks[
        page_offset : page_offset + normalized_page_size + 1
    ]
    has_more = len(page_candidates) > normalized_page_size
    page_ids = [deck.id for deck in page_candidates[:normalized_page_size]]
    if not page_ids:
        results: list[Deck] = []
    else:
        preserved_order = Case(
            *[
                When(id=deck_id, then=Value(position))
                for position, deck_id in enumerate(page_ids)
            ],
            output_field=IntegerField(),
        )
        results = list(
            deck_summary_queryset()
            .filter(id__in=page_ids, visibility="public")
            .order_by(preserved_order)
        )
    return DeckSummaryPage(
        count=count,
        has_more=has_more,
        page=normalized_page,
        page_size=normalized_page_size,
        snapshot_at=snapshot_at,
        results=results,
    )


def list_owner_deck_summary_page(
    owner_id: str,
    *,
    page: int,
    page_size: int,
    snapshot_at: datetime | None = None,
    cursor_created_at: datetime | None = None,
    cursor_id: str | None = None,
    search_query: str | None = None,
    hero_query: str | None = None,
    card_query: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_exclude_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
    deck_tag_ids: list[str] | None = None,
    deck_tag_exclude_ids: list[str] | None = None,
    deck_tag_match: str | None = None,
    card_pool_scope: CardPoolScope,
) -> DeckSummaryPage:
    effective_snapshot_at = snapshot_at or timezone.now()
    queryset = apply_deck_filters(
        deck_summary_queryset().filter(
            owner_id=owner_id,
            created_at__lte=effective_snapshot_at,
        ),
        search_query=search_query,
        hero_query=hero_query,
        author_query=None,
        card_query=card_query,
        affinity_symbol_ids=affinity_symbol_ids,
        affinity_symbol_exclude_ids=affinity_symbol_exclude_ids,
        affinity_symbol_match=affinity_symbol_match,
        deck_tag_ids=deck_tag_ids,
        deck_tag_exclude_ids=deck_tag_exclude_ids,
        deck_tag_match=deck_tag_match,
        card_pool_scope=card_pool_scope,
    ).order_by(*PAGINATED_DECK_ORDERING)
    return _paginate_deck_summary_queryset(
        queryset,
        page=page,
        page_size=page_size,
        snapshot_at=effective_snapshot_at,
        cursor_created_at=cursor_created_at,
        cursor_id=cursor_id,
    )
def _paginate_deck_summary_queryset(
    queryset: QuerySet[Deck],
    *,
    page: int,
    page_size: int,
    snapshot_at: datetime,
    cursor_created_at: datetime | None = None,
    cursor_id: str | None = None,
) -> DeckSummaryPage:
    count = queryset.count()
    normalized_page, normalized_page_size, offset = _pagination_bounds(
        count=count,
        page=page,
        page_size=page_size,
    )
    page_queryset = queryset
    if cursor_created_at is not None and cursor_id is not None:
        page_queryset = page_queryset.filter(
            Q(created_at__lt=cursor_created_at)
            | Q(created_at=cursor_created_at, id__gt=cursor_id)
        )
        offset = 0
    page_results = list(page_queryset[offset : offset + normalized_page_size + 1])
    return DeckSummaryPage(
        count=count,
        has_more=len(page_results) > normalized_page_size,
        page=normalized_page,
        page_size=normalized_page_size,
        snapshot_at=snapshot_at,
        results=page_results[:normalized_page_size],
    )


def _decks_after_cursor(
    decks: list[Deck],
    *,
    cursor_created_at: datetime | None,
    cursor_id: str | None,
) -> list[Deck]:
    if cursor_created_at is None or cursor_id is None:
        return decks
    return [
        deck
        for deck in decks
        if deck.created_at < cursor_created_at
        or (deck.created_at == cursor_created_at and deck.id > cursor_id)
    ]


def _pagination_bounds(*, count: int, page: int, page_size: int) -> tuple[int, int, int]:
    normalized_page_size = max(1, min(page_size, 100))
    last_page = max(1, (count + normalized_page_size - 1) // normalized_page_size)
    normalized_page = min(max(page, 1), last_page)
    return normalized_page, normalized_page_size, (normalized_page - 1) * normalized_page_size


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


def get_deck(deck_id: str) -> Deck | None:
    return deck_queryset().filter(id=deck_id).first()


def get_owner_deck(deck_id: str, owner_id: str) -> Deck | None:
    return deck_queryset().filter(id=deck_id, owner_id=owner_id).first()


def get_owner_deck_by_creation_id(owner_id: str, client_creation_id: UUID) -> Deck | None:
    return deck_queryset().filter(owner_id=owner_id, client_creation_id=client_creation_id).first()


def get_owner_deck_creation(owner_id: str, client_creation_id: UUID) -> DeckCreation | None:
    return DeckCreation.objects.filter(
        owner_id=owner_id,
        client_creation_id=client_creation_id,
    ).first()


def get_deck_for_viewer(deck_id: str, *, viewer_id: str | None = None) -> Deck | None:
    query = deck_queryset().filter(id=deck_id)
    if viewer_id:
        return query.filter(visibility__in=PUBLIC_DECK_VISIBILITIES).first() or query.filter(owner_id=viewer_id).first()
    return query.filter(visibility__in=PUBLIC_DECK_VISIBILITIES).first()
