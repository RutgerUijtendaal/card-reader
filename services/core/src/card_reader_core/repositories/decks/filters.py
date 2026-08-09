from __future__ import annotations

from django.db.models import Q, QuerySet

from card_reader_core.models import CardPool, Deck


def apply_deck_filters(
    queryset: QuerySet[Deck],
    *,
    search_query: str | None = None,
    hero_query: str | None,
    author_query: str | None,
    card_query: str | None,
    affinity_symbol_ids: list[str] | None,
    affinity_symbol_exclude_ids: list[str] | None,
    affinity_symbol_match: str | None,
    deck_tag_ids: list[str] | None,
    deck_tag_exclude_ids: list[str] | None,
    deck_tag_match: str | None,
    card_pool: CardPool | None = None,
) -> QuerySet[Deck]:
    filtered = queryset

    normalized_search_query = (search_query or "").strip()
    if normalized_search_query:
        filtered = filtered.filter(
            Q(name__icontains=normalized_search_query)
            | Q(owner__username__icontains=normalized_search_query)
            | _hero_text_query(normalized_search_query, card_pool)
            | _entry_text_query(normalized_search_query, card_pool)
            | _sideboard_text_query(normalized_search_query, card_pool)
        )

    normalized_hero_query = (hero_query or "").strip()
    if normalized_hero_query:
        filtered = filtered.filter(_hero_text_query(normalized_hero_query, card_pool))

    normalized_author_query = (author_query or "").strip()
    if normalized_author_query:
        filtered = filtered.filter(owner__username__icontains=normalized_author_query)

    normalized_card_query = (card_query or "").strip()
    if normalized_card_query:
        filtered = filtered.filter(
            _entry_text_query(normalized_card_query, card_pool)
            | _sideboard_text_query(normalized_card_query, card_pool)
        )

    normalized_affinity_symbol_ids = [symbol_id.strip() for symbol_id in affinity_symbol_ids or [] if symbol_id.strip()]
    if normalized_affinity_symbol_ids:
        match_all = affinity_symbol_match == "all"
        if match_all:
            for symbol_id in normalized_affinity_symbol_ids:
                filtered = filtered.filter(_affinity_symbol_query(symbol_id, card_pool))
        else:
            affinity_query = Q()
            for symbol_id in normalized_affinity_symbol_ids:
                affinity_query |= _affinity_symbol_query(symbol_id, card_pool)
            filtered = filtered.filter(affinity_query)

    normalized_affinity_symbol_exclude_ids = [
        symbol_id.strip() for symbol_id in affinity_symbol_exclude_ids or [] if symbol_id.strip()
    ]
    if normalized_affinity_symbol_exclude_ids:
        excluded_affinity_query = Q()
        for symbol_id in normalized_affinity_symbol_exclude_ids:
            excluded_affinity_query |= _affinity_symbol_query(symbol_id, card_pool)
        filtered = filtered.exclude(excluded_affinity_query)

    normalized_deck_tag_ids = [tag_id.strip() for tag_id in deck_tag_ids or [] if tag_id.strip()]
    if normalized_deck_tag_ids:
        if deck_tag_match == "all":
            for tag_id in normalized_deck_tag_ids:
                filtered = filtered.filter(tag_assignments__tag_id=tag_id)
        else:
            filtered = filtered.filter(tag_assignments__tag_id__in=normalized_deck_tag_ids)

    normalized_deck_tag_exclude_ids = [
        tag_id.strip() for tag_id in deck_tag_exclude_ids or [] if tag_id.strip()
    ]
    if normalized_deck_tag_exclude_ids:
        filtered = filtered.exclude(tag_assignments__tag_id__in=normalized_deck_tag_exclude_ids)

    return filtered.distinct()


def _hero_text_query(query: str, card_pool: CardPool | None) -> Q:
    result = Q(hero_card__label__icontains=query) | Q(
        hero_card__latest_version__name__icontains=query
    )
    return result if card_pool is None else result & Q(hero_card__card_pool=card_pool)


def _entry_text_query(query: str, card_pool: CardPool | None) -> Q:
    result = Q(entries__card__label__icontains=query) | Q(
        entries__card__latest_version__name__icontains=query
    )
    return result if card_pool is None else result & Q(entries__card__card_pool=card_pool)


def _sideboard_text_query(query: str, card_pool: CardPool | None) -> Q:
    result = Q(sideboards__entries__card__label__icontains=query) | Q(
        sideboards__entries__card__latest_version__name__icontains=query
    )
    return result if card_pool is None else result & Q(
        sideboards__entries__card__card_pool=card_pool
    )


def _affinity_symbol_query(symbol_id: str, card_pool: CardPool | None) -> Q:
    hero_query = Q(
            hero_card__latest_version__card_version_symbols__symbol_id=symbol_id,
            hero_card__latest_version__card_version_symbols__symbol__symbol_type="affinity",
        )
    entry_query = Q(
            entries__card__latest_version__card_version_symbols__symbol_id=symbol_id,
            entries__card__latest_version__card_version_symbols__symbol__symbol_type="affinity",
        )
    sideboard_query = Q(
            sideboards__entries__card__latest_version__card_version_symbols__symbol_id=symbol_id,
            sideboards__entries__card__latest_version__card_version_symbols__symbol__symbol_type="affinity",
        )
    if card_pool is not None:
        hero_query &= Q(hero_card__card_pool=card_pool)
        entry_query &= Q(entries__card__card_pool=card_pool)
        sideboard_query &= Q(sideboards__entries__card__card_pool=card_pool)
    return hero_query | entry_query | sideboard_query
