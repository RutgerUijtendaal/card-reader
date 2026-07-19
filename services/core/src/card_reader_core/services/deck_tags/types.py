from __future__ import annotations

from typing import Literal, TypedDict

from card_reader_core.models import Deck, DeckTag, DeckTagSuggestion


class DeckTagCatalog(TypedDict):
    roles: list[DeckTag]
    types: list[DeckTag]


class AdminDeckTagCatalog(TypedDict):
    roles: list[DeckTag]
    types: list[DeckTag]
    suggested_types: list[DeckTagSuggestion]


class DeckTagDetail(TypedDict):
    entry: DeckTag
    linked_decks: list[Deck]
    linked_deck_count: int


class DeckTagSuggestionDetail(TypedDict):
    entry: DeckTagSuggestion
    linked_decks: list[Deck]
    occurrence_count: int
    active_occurrence_count: int


class DeckTagSuggestionResolution(TypedDict):
    label: str
    normalized_value: str
    status: Literal["pending", "resolved", "rejected"]
    message: str | None
    suggestion_id: str | None
    tag: DeckTag | None
