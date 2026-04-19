from __future__ import annotations

import re
from typing import Any

from PIL import Image

from parsers.ocr_runner import OcrRunner

from .types import RegionParseResult


class StatsRegionParser:
    _number_pattern = re.compile(r"-?\d+")

    def __init__(self, ocr_runner: OcrRunner) -> None:
        self._ocr_runner = ocr_runner

    def parse(
        self,
        *,
        region_name: str,
        field_name: str,
        image: Image.Image,
        region_spec: dict[str, Any],
    ) -> RegionParseResult:
        _ = region_spec
        ocr_data = self._ocr_runner.run(image)
        text = str(ocr_data.get("text", ""))
        value = self._extract_number(text)

        normalized_fields: dict[str, str] = {}
        if value is not None:
            normalized_fields[field_name] = str(value)

        return RegionParseResult(
            region_name=region_name,
            text=text,
            confidence=self._safe_confidence(ocr_data.get("confidence", 0.0)),
            lines=self._safe_lines(ocr_data.get("lines", [])),
            normalized_fields=normalized_fields,
        )

    def _extract_number(self, text: str) -> int | None:
        match = self._number_pattern.search(text)
        if not match:
            return None
        try:
            return int(match.group(0))
        except ValueError:
            return None

    def _safe_confidence(self, raw: Any) -> float:
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    def _safe_lines(self, raw: Any) -> list[dict[str, Any]]:
        return raw if isinstance(raw, list) else []

