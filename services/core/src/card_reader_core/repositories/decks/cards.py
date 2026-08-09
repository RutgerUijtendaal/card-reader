from __future__ import annotations

from card_reader_core.models import PLAYER_CARD_POOL, Card

from .prefetch import latest_version_metadata_prefetches


def get_cards_by_ids(card_ids: list[str]) -> dict[str, Card]:
    if not card_ids:
        return {}
    return {
        card.id: card
        for card in Card.objects.filter(id__in=card_ids, card_pool=PLAYER_CARD_POOL).select_related(
            "latest_version",
            "latest_version__template",
            "latest_version__previous_version",
        ).prefetch_related("role_assignments", *latest_version_metadata_prefetches("latest_version"))
    }


def get_deck_card(card_id: str) -> Card | None:
    return (
        Card.objects.filter(id=card_id, card_pool=PLAYER_CARD_POOL)
        .select_related("latest_version", "latest_version__template", "latest_version__previous_version")
        .prefetch_related("role_assignments", *latest_version_metadata_prefetches("latest_version"))
        .first()
    )
