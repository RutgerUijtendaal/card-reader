from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from card_reader_core.models import CardVersion, CardVersionImage, Keyword, Symbol, Tag, Type


@dataclass(frozen=True)
class LatestCardVersionReparseSource:
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
