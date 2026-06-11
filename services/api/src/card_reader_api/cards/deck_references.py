from __future__ import annotations

from card_reader_api.cards.serializers import card_deck_reference_payload
from card_reader_api.decks.serializers import deck_payload
from card_reader_core.services.decks import DeckService

CARD_DETAIL_DECK_REFERENCE_LIMIT = 3


def card_deck_references_payload(
    card_id: str,
    *,
    viewer_id: str | None,
    limit: int = CARD_DETAIL_DECK_REFERENCE_LIMIT,
) -> list[dict[str, object]]:
    return [
        {
            **deck_payload(deck),
            "card_reference": card_deck_reference_payload(deck, card_id=card_id),
        }
        for deck in DeckService().list_card_decks_for_viewer(card_id, viewer_id=viewer_id)[:limit]
    ]
