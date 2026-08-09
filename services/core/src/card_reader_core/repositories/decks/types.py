from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from card_reader_core.models import Deck


@dataclass(frozen=True)
class DeckSummaryPage:
    count: int
    has_more: bool
    page: int
    page_size: int
    snapshot_at: datetime
    results: list[Deck]
