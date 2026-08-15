from __future__ import annotations

from collections.abc import Iterator

from card_reader_core.models import Card, CardPoolScope, Deck


def iter_deck_cards(deck: Deck) -> Iterator[Card]:
    """Yield every card referenced by a loaded deck without deduplicating identities."""
    yield deck.hero_card
    for entry in deck.entries.all():
        yield entry.card
    for sideboard in deck.sideboards.all():
        for sideboard_entry in sideboard.entries.all():
            yield sideboard_entry.card


def deck_uses_out_of_scope_card(deck: Deck, card_pool_scope: CardPoolScope) -> bool:
    return any(
        not card_pool_scope.allows_card_pool(card.card_pool)
        for card in iter_deck_cards(deck)
    )


def deck_export_uses_out_of_scope_card(
    deck: Deck,
    card_pool_scope: CardPoolScope,
    *,
    sideboard_id: str | None,
) -> bool:
    if sideboard_id is None:
        cards = [deck.hero_card, *(entry.card for entry in deck.entries.all())]
    else:
        cards = [
            entry.card
            for sideboard in deck.sideboards.all()
            if sideboard.id == sideboard_id
            for entry in sideboard.entries.all()
        ]
    return any(not card_pool_scope.allows_card_pool(card.card_pool) for card in cards)


__all__ = [
    "deck_export_uses_out_of_scope_card",
    "deck_uses_out_of_scope_card",
    "iter_deck_cards",
]
