from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class ParsedMetadataSuggestion:
    display_value: str
    normalized_value: str
    source_text: str
    normalized_source_text: str


@dataclass(slots=True)
class ParsedCard:
    checksum: str
    normalized_fields: dict[str, str]
    confidence: dict[str, float]
    raw_ocr: dict[str, Any]
    keyword_ids: list[str]
    tag_ids: list[str]
    type_ids: list[str]
    symbol_ids: list[str]
    tag_suggestions: list[ParsedMetadataSuggestion]
    type_suggestions: list[ParsedMetadataSuggestion]

