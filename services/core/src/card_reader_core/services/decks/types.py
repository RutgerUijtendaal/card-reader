from __future__ import annotations

from dataclasses import dataclass

from card_reader_core.models import DeckVisibility

MAX_DECK_COPIES = 4
MIN_MAINBOARD_CARD_COUNT = 20
MAX_MAINBOARD_CARD_COUNT = 100
MIN_MAINBOARD_MANA_TYPE_COUNT = 3
MAX_SIDEBOARD_ENTRY_QUANTITY = 100


@dataclass(frozen=True)
class DeckEntryInput:
    card_id: str
    quantity: int


@dataclass(frozen=True)
class DeckValidationSummary:
    is_valid: bool
    status_label: str
    total_cards: int
    unique_cards: int
    issues: list[str]
    warnings: list[str]
    deprecated_card_count: int = 0
    deprecated_card_ids: list[str] | None = None


@dataclass(frozen=True)
class DeckSideboardInput:
    name: str
    entries: list[DeckEntryInput]


@dataclass(frozen=True)
class DeckTotals:
    overall_total_cards: int
    overall_unique_cards: int
    mainboard_total_cards: int
    mainboard_unique_cards: int


@dataclass(frozen=True)
class DeckUpdateInput:
    name: str | None = None
    description: str | None = None
    visibility: DeckVisibility | None = None
    hero_card_id: str | None = None
    entries: list[DeckEntryInput] | None = None
    sideboards: list[DeckSideboardInput] | None = None
    update_name: bool = False
    update_description: bool = False
    update_visibility: bool = False
    update_hero_card_id: bool = False
    update_entries: bool = False
    update_sideboards: bool = False
