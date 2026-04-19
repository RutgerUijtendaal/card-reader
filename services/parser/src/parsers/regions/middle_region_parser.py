from __future__ import annotations

from typing import Any

from PIL import Image

from extractors import TagsExtractor, TypesExtractor
from parsers.ocr_runner import OcrRunner

from .types import RegionParseResult


class MiddleRegionParser:
    def __init__(
        self,
        ocr_runner: OcrRunner,
        tags_extractor: TagsExtractor,
        types_extractor: TypesExtractor,
    ) -> None:
        self._ocr_runner = ocr_runner
        self._tags_extractor = tags_extractor
        self._types_extractor = types_extractor

    def parse(
        self,
        *,
        region_name: str,
        image: Image.Image,
        region_spec: dict[str, Any],
    ) -> RegionParseResult:
        _ = region_spec
        ocr_data = self._ocr_runner.run(image)
        text = str(ocr_data.get("text", ""))
        tags = self._tags_extractor.extract(text)
        types = self._types_extractor.extract(text)

        return RegionParseResult(
            region_name=region_name,
            text=text,
            confidence=self._safe_confidence(ocr_data.get("confidence", 0.0)),
            lines=self._safe_lines(ocr_data.get("lines", [])),
            normalized_fields={"type_line": text},
            extracted_tags=tags,
            extracted_types=types,
        )

    def _safe_confidence(self, raw: Any) -> float:
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    def _safe_lines(self, raw: Any) -> list[dict[str, Any]]:
        return raw if isinstance(raw, list) else []

