from __future__ import annotations

from card_reader_core.models import CardBack, CardBackPoolDefault, is_card_pool
from card_reader_core.repositories.card_backs import get_card_back, upsert_pool_default

from .assets import resolve_card_back_image_asset_path


def set_pool_default(card_pool: object, card_back_id: str) -> CardBackPoolDefault:
    if not is_card_pool(card_pool):
        raise ValueError("Invalid card pool.")
    card_back = select_card_back_override(card_back_id)
    if card_back is None:
        raise ValueError("Card back is required.")
    return upsert_pool_default(card_pool=card_pool, card_back=card_back)


def select_card_back_override(card_back_id: str | None) -> CardBack | None:
    if card_back_id is None:
        return None
    card_back = get_card_back(card_back_id)
    if card_back is None:
        raise ValueError("Card back was not found.")
    if resolve_card_back_image_asset_path(card_back) is None:
        raise ValueError("Card back image file is missing.")
    return card_back
