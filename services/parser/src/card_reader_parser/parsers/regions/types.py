from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..symbol_detector import DetectedSymbol


@dataclass(slots=True)
class RegionParseResult:
    region_name: str
    text: str = ""
    confidence: float = 0.0
    lines: list[dict[str, Any]] = field(default_factory=list)
    detected_symbols: list[DetectedSymbol] = field(default_factory=list)
    normalized_fields: dict[str, str] = field(default_factory=dict)
    extracted_keyword_ids: list[str] = field(default_factory=list)
    extracted_tags: list[str] = field(default_factory=list)
    extracted_types: list[str] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)



