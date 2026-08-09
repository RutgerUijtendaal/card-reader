from __future__ import annotations

from dataclasses import dataclass

from card_reader_core.models import Deck


@dataclass(frozen=True)
class DeckSummaryPage:
    count: int
    page: int
    page_size: int
    results: list[Deck]
