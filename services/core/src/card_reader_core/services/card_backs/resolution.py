from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, cast

from card_reader_core.models import (
    CARD_FACTIONS,
    CARD_POOLS,
    EVIL_CARD_POOL,
    CardBack,
    CardFaction,
    CardPool,
    card_faction_keys,
)
from card_reader_core.repositories.card_backs import (
    get_cards_for_card_back_resolution,
    get_faction_default_rows,
    get_pool_default_rows,
)

CardBackResolutionSource = Literal["override", "faction_default", "pool_default"]


@dataclass(frozen=True)
class ResolvedCardBack:
    card_id: str
    card_pool: CardPool
    source: CardBackResolutionSource | None
    card_back: CardBack | None
    faction: CardFaction | None = None


def get_pool_card_back_defaults() -> dict[CardPool, CardBack | None]:
    defaults: dict[CardPool, CardBack | None] = {card_pool: None for card_pool in CARD_POOLS}
    for row in get_pool_default_rows():
        defaults[row.card_pool] = row.card_back
    return defaults


def get_faction_card_back_defaults() -> dict[CardFaction, CardBack | None]:
    defaults: dict[CardFaction, CardBack | None] = {
        faction: None for faction in CARD_FACTIONS
    }
    for row in get_faction_default_rows():
        defaults[row.faction] = row.card_back
    return defaults


def resolve_effective_card_backs(card_ids: Iterable[str]) -> dict[str, ResolvedCardBack]:
    unique_ids = list(dict.fromkeys(str(card_id) for card_id in card_ids))
    if not unique_ids:
        return {}
    pool_defaults = get_pool_card_back_defaults()
    faction_defaults = get_faction_card_back_defaults()
    resolved: dict[str, ResolvedCardBack] = {}
    for card in get_cards_for_card_back_resolution(unique_ids):
        card_pool = cast(CardPool, card.card_pool)
        resolved_faction: CardFaction | None = None
        if card.card_back_override is not None:
            source: CardBackResolutionSource | None = "override"
            resolved_card_back: CardBack | None = card.card_back_override
        else:
            resolved_card_back = None
            source = None
            if card_pool == EVIL_CARD_POOL:
                for faction in card_faction_keys(card):
                    faction_default = faction_defaults[faction]
                    if faction_default is None:
                        continue
                    resolved_faction = faction
                    resolved_card_back = faction_default
                    source = "faction_default"
                    break
            if resolved_card_back is None:
                resolved_card_back = pool_defaults[card_pool]
                source = "pool_default" if resolved_card_back is not None else None
        resolved[card.id] = ResolvedCardBack(
            card_id=card.id,
            card_pool=card_pool,
            source=source,
            card_back=resolved_card_back,
            faction=resolved_faction,
        )
    return resolved
