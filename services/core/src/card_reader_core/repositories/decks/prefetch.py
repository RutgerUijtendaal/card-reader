from __future__ import annotations

from django.db.models import Prefetch, QuerySet

from card_reader_core.models import (
    CardVersionKeyword,
    CardVersionSymbol,
    CardVersionTag,
    CardVersionType,
    Deck,
    DeckEntry,
    DeckSideboard,
    DeckSideboardEntry,
)


def deck_queryset() -> QuerySet[Deck]:
    return Deck.objects.select_related(
        "owner",
        "hero_card",
        "hero_card__latest_version",
        "hero_card__latest_version__template",
        "hero_card__latest_version__previous_version",
    ).prefetch_related(
        *latest_version_metadata_prefetches("hero_card__latest_version"),
        Prefetch(
            "entries",
            queryset=DeckEntry.objects.select_related(
                "card",
                "card__latest_version",
                "card__latest_version__template",
                "card__latest_version__previous_version",
            ).prefetch_related(*latest_version_metadata_prefetches("card__latest_version")).order_by("position", "card_id"),
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
                    .prefetch_related(*latest_version_metadata_prefetches("card__latest_version"))
                    .order_by("position", "card_id"),
                )
            ).order_by("created_at", "id"),
        ),
    )


def latest_version_metadata_prefetches(prefix: str) -> tuple[Prefetch[str], ...]:
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
