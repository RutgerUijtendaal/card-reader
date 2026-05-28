from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from card_reader_core.models import Keyword, Symbol, Tag, Type


class CardParserProtocol(Protocol):
    def parse(
        self,
        image_path: Path,
        template_id: str,
        *,
        symbols: list[Symbol],
        known_keywords: list[Keyword],
        known_tags: list[Tag],
        known_types: list[Type],
    ) -> Any:
        pass


@dataclass(frozen=True)
class JobOptions:
    reparse_existing: bool
    keyword_keys: set[str] | None


@dataclass(frozen=True)
class ParserResources:
    known_keywords: list[Keyword]
    known_tags: list[Tag]
    known_types: list[Type]
    detectable_symbols: list[Symbol]


@dataclass(frozen=True)
class ItemProcessingResult:
    checksum: str
    confidence: float
    keyword_count: int
    symbol_count: int
    tag_count: int
    type_count: int
