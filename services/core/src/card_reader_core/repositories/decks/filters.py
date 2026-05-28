from __future__ import annotations

from django.db.models import Q, QuerySet

from card_reader_core.models import Deck


def apply_public_deck_filters(
    queryset: QuerySet[Deck],
    *,
    hero_query: str | None,
    card_query: str | None,
    affinity_symbol_ids: list[str] | None,
    affinity_symbol_exclude_ids: list[str] | None,
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

    normalized_affinity_symbol_exclude_ids = [
        symbol_id.strip() for symbol_id in affinity_symbol_exclude_ids or [] if symbol_id.strip()
    ]
    if normalized_affinity_symbol_exclude_ids:
        excluded_affinity_query = Q()
        for symbol_id in normalized_affinity_symbol_exclude_ids:
            excluded_affinity_query |= _affinity_symbol_query(symbol_id)
        filtered = filtered.exclude(excluded_affinity_query)

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
