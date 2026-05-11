from __future__ import annotations

import logging
from typing import Any

from card_reader_core.models import Tag, Type
from PIL import Image

from ...extractors import KnownMetadataExtractor
from ..ocr_runner import OcrRunner

from .types import RegionParseResult

logger = logging.getLogger(__name__)


class MiddleRegionParser:
    def __init__(
        self,
        ocr_runner: OcrRunner,
        metadata_extractor: KnownMetadataExtractor,
    ) -> None:
        self._ocr_runner = ocr_runner
        self._metadata_extractor = metadata_extractor

    def parse(
        self,
        *,
        region_name: str,
        image: Image.Image,
        region_spec: dict[str, Any],
        known_tags: list[Tag],
        known_types: list[Type],
    ) -> RegionParseResult:
        _ = region_spec
        logger.info("Middle region parse started. region=%s image_size=%sx%s", region_name, image.width, image.height)
        ocr_data = self._ocr_runner.run(image)
        text = str(ocr_data.get("text", ""))
        type_text, tag_text = self._split_middle_text(text)
        tag_ids = self._metadata_extractor.extract_ids(tag_text, known_tags)
        type_ids = self._metadata_extractor.extract_ids(type_text, known_types)
        confidence = self._safe_confidence(ocr_data.get("confidence", 0.0))
        lines = self._safe_lines(ocr_data.get("lines", []))
        logger.info(
            "Middle region parse finished. region=%s conf=%.3f text_len=%s lines=%s tags=%s types=%s",
            region_name,
            confidence,
            len(text),
            len(lines),
            len(tag_ids),
            len(type_ids),
        )

        return RegionParseResult(
            region_name=region_name,
            text=text,
            confidence=confidence,
            lines=lines,
            normalized_fields={"type_line": text},
            extracted_tag_ids=tag_ids,
            extracted_type_ids=type_ids,
        )

    def _safe_confidence(self, raw: Any) -> float:
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    def _safe_lines(self, raw: Any) -> list[dict[str, Any]]:
        return raw if isinstance(raw, list) else []

    def _split_middle_text(self, middle_text: str) -> tuple[str, str]:
        text = " ".join(middle_text.split()).strip()
        if not text:
            return "", ""
        if "-" not in text:
            return text, ""
        left, right = text.split("-", 1)
        return left.strip(), right.strip()


