from __future__ import annotations

from django.db.models import Q, QuerySet

from card_reader_core.models import CardVersion


def apply_card_search(queryset: QuerySet[CardVersion], query: str | None) -> QuerySet[CardVersion]:
    if not query or not query.strip():
        return queryset

    value = query.strip()
    return queryset.filter(
        Q(name__icontains=value)
        | Q(type_line__icontains=value)
        | Q(rules_text__icontains=value)
        | Q(mana_cost__icontains=value)
    )
