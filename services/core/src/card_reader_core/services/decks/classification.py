from __future__ import annotations

from collections.abc import Iterator

from card_reader_core.models import PLAYER_CARD_POOL, Card, Deck


def iter_deck_cards(deck: Deck) -> Iterator[Card]:
    """Yield every card referenced by a loaded deck without deduplicating identities."""
    yield deck.hero_card
    for entry in deck.entries.all():
        yield entry.card
    for sideboard in deck.sideboards.all():
        for sideboard_entry in sideboard.entries.all():
            yield sideboard_entry.card


def deck_uses_non_player_card(deck: Deck) -> bool:
    return any(card.card_pool != PLAYER_CARD_POOL for card in iter_deck_cards(deck))


def deck_export_uses_non_player_card(
    deck: Deck,
    *,
    sideboard_id: str | None,
) -> bool:
    if sideboard_id is None:
        cards = [deck.hero_card, *(entry.card for entry in deck.entries.all())]
    else:
        cards = []
        for sideboard in deck.sideboards.all():
            if sideboard.id != sideboard_id:
                continue
            cards.extend(entry.card for entry in sideboard.entries.all())
    return any(card.card_pool != PLAYER_CARD_POOL for card in cards)


__all__ = [
    "deck_export_uses_non_player_card",
    "deck_uses_non_player_card",
    "iter_deck_cards",
]
