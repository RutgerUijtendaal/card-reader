from __future__ import annotations

from dataclasses import dataclass

from card_reader_core.models import DEFAULT_CARD_POOL, CardPool, CardRole

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class ImportJobItemTarget:
    card_id: str
    card_version_id: str
    card_pool: CardPool = DEFAULT_CARD_POOL
    card_roles: tuple[CardRole, ...] = ()
