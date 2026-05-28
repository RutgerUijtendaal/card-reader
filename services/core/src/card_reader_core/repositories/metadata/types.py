from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from card_reader_core.models import Keyword, MetadataSuggestion, Symbol, Tag, Type

MetadataModel = Keyword | Tag | Symbol | Type
MetadataRow = TypeVar("MetadataRow", bound=MetadataModel)
MANA_TYPE_KEY = "mana"


@dataclass(frozen=True)
class SuggestionCandidate:
    display_value: str
    normalized_value: str
    source_text: str
    normalized_source_text: str


@dataclass(frozen=True)
class MetadataSuggestionListRow:
    suggestion: MetadataSuggestion
    occurrence_count: int
