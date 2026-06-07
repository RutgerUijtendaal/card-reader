from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from card_reader_core.models import CardVersionParseFlag

ParseFlagItemStatus = Literal["open", "resolved", "dismissed"]
ParseFlagStatusFilter = ParseFlagItemStatus | Literal["all"]
PARSE_FLAG_OPEN_STATUS: ParseFlagItemStatus = "open"


@dataclass(frozen=True)
class ParseFlagItemInput:
    property_key: str
    expected_value: str = ""
    note: str = ""


@dataclass(frozen=True)
class PaginatedParseFlags:
    count: int
    page: int
    page_size: int
    results: list[CardVersionParseFlag]
