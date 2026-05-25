from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict

from card_reader_core.models import CardVersion, CardVersionImage, Keyword, Symbol, Tag, Type

CardSort = Literal["updated_desc", "name_asc", "mana_asc", "mana_desc"]
CARD_SORT_UPDATED_DESC: CardSort = "updated_desc"
CARD_SORT_NAME_ASC: CardSort = "name_asc"
CARD_SORT_MANA_ASC: CardSort = "mana_asc"
CARD_SORT_MANA_DESC: CardSort = "mana_desc"
CARD_SORT_VALUES: tuple[CardSort, ...] = (
    CARD_SORT_UPDATED_DESC,
    CARD_SORT_NAME_ASC,
    CARD_SORT_MANA_ASC,
    CARD_SORT_MANA_DESC,
)
DEFAULT_CARD_PAGE_SIZE = 36


@dataclass(frozen=True)
class LatestCardVersionReparseSource:
    card_id: str
    card_version_id: str
    template_id: str
    image_path: Path


@dataclass(frozen=True)
class CardListRow:
    version: CardVersion
    image: CardVersionImage | None
    keywords: list[Keyword]
    tags: list[Tag]
    symbols: list[Symbol]
    types: list[Type]


@dataclass(frozen=True)
class PaginatedCardList:
    count: int
    page: int
    page_size: int
    results: list[CardListRow]


class FieldSourcesPayload(TypedDict):
    fields: dict[str, str]
    metadata: dict[str, str]


class ParsedSnapshotPayload(TypedDict):
    fields: dict[str, object]
    metadata: dict[str, list[str]]
