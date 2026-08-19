from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, cast

from card_reader_core.models import CARD_POOLS, CardBack, CardPool
from card_reader_core.repositories.card_backs import (
    get_cards_for_card_back_resolution,
    get_pool_default_rows,
)

CardBackResolutionSource = Literal["override", "pool_default"]


@dataclass(frozen=True)
class ResolvedCardBack:
    card_id: str
    card_pool: CardPool
    source: CardBackResolutionSource | None
    card_back: CardBack | None


def get_pool_card_back_defaults() -> dict[CardPool, CardBack | None]:
    defaults: dict[CardPool, CardBack | None] = {card_pool: None for card_pool in CARD_POOLS}
    for row in get_pool_default_rows():
        defaults[row.card_pool] = row.card_back
    return defaults


def resolve_effective_card_backs(card_ids: Iterable[str]) -> dict[str, ResolvedCardBack]:
    unique_ids = list(dict.fromkeys(str(card_id) for card_id in card_ids))
    if not unique_ids:
        return {}
    defaults = get_pool_card_back_defaults()
    resolved: dict[str, ResolvedCardBack] = {}
    for card in get_cards_for_card_back_resolution(unique_ids):
        card_pool = cast(CardPool, card.card_pool)
        if card.card_back_override is not None:
            source: CardBackResolutionSource | None = "override"
            resolved_card_back: CardBack | None = card.card_back_override
        else:
            resolved_card_back = defaults[card_pool]
            source = "pool_default" if resolved_card_back is not None else None
        resolved[card.id] = ResolvedCardBack(
            card_id=card.id,
            card_pool=card_pool,
            source=source,
            card_back=resolved_card_back,
        )
    return resolved
