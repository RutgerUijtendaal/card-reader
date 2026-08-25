from __future__ import annotations

from django.db.models import Q, QuerySet

from card_reader_core.models import Deck


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
) -> QuerySet[Deck]:
    filtered = queryset

    normalized_search_query = (search_query or "").strip()
    if normalized_search_query:
        filtered = filtered.filter(
            Q(name__icontains=normalized_search_query)
            | Q(owner__username__icontains=normalized_search_query)
            | _hero_text_query(normalized_search_query)
            | _entry_text_query(normalized_search_query)
            | _sideboard_text_query(normalized_search_query)
        )

    normalized_hero_query = (hero_query or "").strip()
    if normalized_hero_query:
        filtered = filtered.filter(_hero_text_query(normalized_hero_query))

    normalized_author_query = (author_query or "").strip()
    if normalized_author_query:
        filtered = filtered.filter(owner__username__icontains=normalized_author_query)

    normalized_card_query = (card_query or "").strip()
    if normalized_card_query:
        filtered = filtered.filter(
            _entry_text_query(normalized_card_query)
            | _sideboard_text_query(normalized_card_query)
        )

    normalized_affinity_symbol_ids = _normalize_filter_ids(affinity_symbol_ids)
    if normalized_affinity_symbol_ids:
        filtered = _filter_affinity_symbols(
            filtered,
            symbol_ids=normalized_affinity_symbol_ids,
            match_all=affinity_symbol_match == "all",
        )

    normalized_affinity_symbol_exclude_ids = _normalize_filter_ids(
        affinity_symbol_exclude_ids
    )
    if normalized_affinity_symbol_exclude_ids:
        excluded_affinity_query = _combined_affinity_query(
            normalized_affinity_symbol_exclude_ids
        )
        filtered = filtered.exclude(excluded_affinity_query)

    normalized_deck_tag_ids = _normalize_filter_ids(deck_tag_ids)
    if normalized_deck_tag_ids:
        filtered = _filter_deck_tags(
            filtered,
            tag_ids=normalized_deck_tag_ids,
            match_all=deck_tag_match == "all",
        )

    normalized_deck_tag_exclude_ids = _normalize_filter_ids(deck_tag_exclude_ids)
    if normalized_deck_tag_exclude_ids:
        filtered = filtered.exclude(tag_assignments__tag_id__in=normalized_deck_tag_exclude_ids)

    return filtered.distinct()


def _normalize_filter_ids(values: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for value in values or []:
        stripped_value = value.strip()
        if stripped_value:
            normalized.append(stripped_value)
    return normalized


def _filter_affinity_symbols(
    queryset: QuerySet[Deck],
    *,
    symbol_ids: list[str],
    match_all: bool,
) -> QuerySet[Deck]:
    if not match_all:
        return queryset.filter(_combined_affinity_query(symbol_ids))
    filtered = queryset
    for symbol_id in symbol_ids:
        filtered = filtered.filter(_affinity_symbol_query(symbol_id))
    return filtered


def _combined_affinity_query(symbol_ids: list[str]) -> Q:
    combined_query = Q()
    for symbol_id in symbol_ids:
        combined_query |= _affinity_symbol_query(symbol_id)
    return combined_query


def _filter_deck_tags(
    queryset: QuerySet[Deck],
    *,
    tag_ids: list[str],
    match_all: bool,
) -> QuerySet[Deck]:
    if not match_all:
        return queryset.filter(tag_assignments__tag_id__in=tag_ids)
    filtered = queryset
    for tag_id in tag_ids:
        filtered = filtered.filter(tag_assignments__tag_id=tag_id)
    return filtered


def _hero_text_query(query: str) -> Q:
    return Q(hero_card__label__icontains=query) | Q(
        hero_card__latest_version__name__icontains=query
    )


def _entry_text_query(query: str) -> Q:
    return Q(entries__card__label__icontains=query) | Q(
        entries__card__latest_version__name__icontains=query
    )


def _sideboard_text_query(query: str) -> Q:
    return Q(sideboards__entries__card__label__icontains=query) | Q(
        sideboards__entries__card__latest_version__name__icontains=query
    )


def _affinity_symbol_query(symbol_id: str) -> Q:
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
    return hero_query | entry_query | sideboard_query
