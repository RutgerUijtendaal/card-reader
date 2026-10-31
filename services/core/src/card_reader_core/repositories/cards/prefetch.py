from __future__ import annotations

from django.db.models import Prefetch

from card_reader_core.models import (
    CardVersionKeyword,
    CardVersionSymbol,
    CardVersionTag,
    CardVersionType,
)


def card_version_metadata_prefetches(prefix: str = "") -> tuple[Prefetch[str], ...]:
    """Load each metadata link together with its catalog row in one query."""
    path = f"{prefix}__" if prefix else ""
    return (
        Prefetch(
            f"{path}card_version_keywords",
            queryset=CardVersionKeyword.objects.select_related("keyword").order_by("keyword__label"),
        ),
        Prefetch(
            f"{path}card_version_tags",
            queryset=CardVersionTag.objects.select_related("tag").order_by("tag__label"),
        ),
        Prefetch(
            f"{path}card_version_symbols",
            queryset=CardVersionSymbol.objects.select_related("symbol").order_by("symbol__label"),
        ),
        Prefetch(
            f"{path}card_version_types",
            queryset=CardVersionType.objects.select_related("type").order_by("type__label"),
        ),
    )
