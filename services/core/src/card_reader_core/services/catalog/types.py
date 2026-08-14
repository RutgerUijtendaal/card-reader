from __future__ import annotations

from typing import TypedDict

from card_reader_core.models import Keyword, Symbol, Tag, Type


class CatalogData(TypedDict):
    known: "KnownCatalogData"
    suggested: "SuggestedCatalogData"


class KnownCatalogData(TypedDict):
    keywords: list[Keyword]
    tags: list[Tag]
    symbols: list[Symbol]
    types: list[Type]


class SuggestedCatalogData(TypedDict):
    tags: list["CatalogSuggestionDetail"]
    types: list["CatalogSuggestionDetail"]


class SuggestionOccurrencePreview(TypedDict):
    card_id: str
    card_label: str
    card_version_id: str
    card_version_name: str
    image_url: str | None
    source_text: str
    normalized_source_text: str
    card_pool: str
    card_roles: list[str]
    card_factions: list[str]


class LinkedCardPreview(TypedDict):
    card_id: str
    card_label: str
    card_version_id: str
    card_version_name: str
    image_url: str | None
    card_pool: str
    card_roles: list[str]
    card_factions: list[str]


class CatalogSuggestionDetail(TypedDict):
    id: str
    kind: str
    display_value: str
    normalized_value: str
    status: str
    occurrence_count: int
    accepted_tag: Tag | None
    accepted_type: Type | None
    occurrences: list[SuggestionOccurrencePreview]


class KeywordDetail(TypedDict):
    entry: Keyword
    linked_cards: list[LinkedCardPreview]
    linked_card_count: int


class TagDetail(TypedDict):
    entry: Tag
    linked_cards: list[LinkedCardPreview]
    linked_card_count: int
    classification_rules: list[dict[str, object]]


class TypeDetail(TypedDict):
    entry: Type
    linked_cards: list[LinkedCardPreview]
    linked_card_count: int
    classification_rules: list[dict[str, object]]


class SymbolDetail(TypedDict):
    entry: Symbol
    linked_cards: list[LinkedCardPreview]
    linked_card_count: int
