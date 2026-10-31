from __future__ import annotations

from django.db.models import Prefetch, QuerySet

from card_reader_core.models import (
    Card,
    CardVersionImage,
    CardVersionKeyword,
    CardVersionSymbol,
    CardVersionTag,
    CardVersionType,
    Deck,
    DeckEntry,
    DeckSideboard,
    DeckSideboardEntry,
    DeckTagAssignment,
    DeckTagSuggestionDeck,
)


def deck_queryset() -> QuerySet[Deck]:
    cards = _deck_cards_queryset().select_related(
        "latest_version__template", "latest_version__content_version",
    ).defer("latest_version__template__definition_json").prefetch_related(
        Prefetch(
            "latest_version__images",
            queryset=CardVersionImage.objects.order_by("-created_at"),
        ),
        *latest_version_metadata_prefetches("latest_version"),
    )
    return _decks_with_cards(cards, cards).select_related("owner").prefetch_related(
        *deck_metadata_prefetches(),
    )


def deck_summary_queryset() -> QuerySet[Deck]:
    hero_cards = _deck_cards_queryset().prefetch_related(
        Prefetch(
            "latest_version__images",
            queryset=CardVersionImage.objects.order_by("-created_at"),
        ),
        *summary_version_symbol_prefetches("latest_version"),
    )
    entry_cards = _deck_cards_queryset().prefetch_related(
        *summary_version_type_prefetches("latest_version"),
    )
    return _decks_with_cards(hero_cards, entry_cards).select_related("owner").prefetch_related(
        *deck_metadata_prefetches(),
    )


def deck_validation_queryset() -> QuerySet[Deck]:
    cards = _deck_cards_queryset()
    entry_cards = cards.prefetch_related(*summary_version_type_prefetches("latest_version"))
    return _decks_with_cards(cards, entry_cards)


def _deck_cards_queryset() -> QuerySet[Card]:
    return Card.objects.select_related("latest_version").defer(
        "latest_version__parsed_snapshot_json",
        "latest_version__field_sources_json",
    ).prefetch_related("role_assignments", "faction_assignments", "mana_family_assignments")


def _decks_with_cards(
    hero_cards: QuerySet[Card], entry_cards: QuerySet[Card],
) -> QuerySet[Deck]:
    # Prefetch shared Card objects once per board batch, rather than joining and
    # decoding the same version (including JSON) for every entry in every deck.
    return Deck.objects.prefetch_related(
        Prefetch("hero_card", queryset=hero_cards),
        Prefetch(
            "entries",
            queryset=DeckEntry.objects.prefetch_related(
                Prefetch("card", queryset=entry_cards),
            ).order_by("position", "card_id"),
        ),
        Prefetch(
            "sideboards",
            queryset=DeckSideboard.objects.prefetch_related(
                Prefetch(
                    "entries",
                    queryset=DeckSideboardEntry.objects.prefetch_related(
                        Prefetch("card", queryset=entry_cards),
                    ).order_by("position", "card_id"),
                ),
            ).order_by("created_at", "id"),
        ),
    )


def deck_metadata_prefetches() -> tuple[Prefetch[str], ...]:
    return (
        Prefetch(
            "tag_assignments",
            queryset=DeckTagAssignment.objects.select_related("tag").order_by("tag__kind", "tag__label"),
        ),
        Prefetch(
            "tag_suggestion_occurrences",
            queryset=DeckTagSuggestionDeck.objects.select_related("suggestion")
            .filter(suggestion__status="pending", is_active=True)
            .order_by("suggestion__display_value"),
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


def summary_version_symbol_prefetches(prefix: str) -> tuple[Prefetch[str], ...]:
    return (
        Prefetch(
            f"{prefix}__card_version_symbols",
            queryset=CardVersionSymbol.objects.select_related("symbol")
            .filter(symbol__symbol_type="affinity")
            .order_by("symbol__label"),
        ),
    )


def summary_version_type_prefetches(prefix: str) -> tuple[Prefetch[str], ...]:
    return (
        Prefetch(
            f"{prefix}__card_version_types",
            queryset=CardVersionType.objects.select_related("type").order_by("type__label"),
        ),
    )
