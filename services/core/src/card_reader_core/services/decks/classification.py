from __future__ import annotations

from collections.abc import Iterator

from card_reader_core.models import Card, CardPool, Deck


def iter_deck_cards(deck: Deck) -> Iterator[Card]:
    """Yield every card referenced by a loaded deck without deduplicating identities."""
    yield deck.hero_card
    for entry in deck.entries.all():
        yield entry.card
    for sideboard in deck.sideboards.all():
        for sideboard_entry in sideboard.entries.all():
            yield sideboard_entry.card


def deck_uses_card_pool(deck: Deck, card_pool: CardPool) -> bool:
    return any(card.card_pool == card_pool for card in iter_deck_cards(deck))


__all__ = ["deck_uses_card_pool", "iter_deck_cards"]
