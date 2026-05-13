from __future__ import annotations

import logging
from typing import Any

from card_reader_core.models import Keyword, Symbol
from PIL import Image

from ...extractors import KnownMetadataExtractor
from ..ocr_runner import OcrRunner
from ..symbol_detector import SymbolDetector

from .types import RegionParseResult

logger = logging.getLogger(__name__)


class BottomRegionParser:
    _EXPECTED_SYMBOL_TYPES = {"mana", "devotion", "generic"}

    def __init__(
        self,
        ocr_runner: OcrRunner,
        symbol_detector: SymbolDetector,
        metadata_extractor: KnownMetadataExtractor,
    ) -> None:
        self._ocr_runner = ocr_runner
        self._symbol_detector = symbol_detector
        self._metadata_extractor = metadata_extractor

    def parse(
        self,
        *,
        region_name: str,
        image: Image.Image,
        region_spec: dict[str, Any],
        symbols: list[Symbol],
        known_keywords: list[Keyword],
    ) -> RegionParseResult:
        _ = region_spec
        logger.info("Bottom region parse started. region=%s image_size=%sx%s", region_name, image.width, image.height)
        logger.info("Bottom region OCR step started. region=%s", region_name)
        ocr_data = self._ocr_runner.run(image)
        logger.info(
            "Bottom region OCR step finished. region=%s conf=%.3f",
            region_name,
            self._safe_confidence(ocr_data.get("confidence", 0.0)),
        )
        text = str(ocr_data.get("text", ""))
        logger.info(
            "Bottom region symbol detection step started. region=%s symbol_candidates=%s expected_types=%s",
            region_name,
            len(symbols),
            sorted(self._EXPECTED_SYMBOL_TYPES),
        )
        detected_symbols = self._symbol_detector.detect(
            image=image,
            symbols=symbols,
            expected_symbol_types=self._EXPECTED_SYMBOL_TYPES,
        )
        logger.info(
            "Bottom region symbol detection step finished. region=%s symbols=%s",
            region_name,
            len(detected_symbols),
        )
        logger.info(
            "Bottom region keyword extraction step started. region=%s known_keywords=%s",
            region_name,
            len(known_keywords),
        )
        keyword_ids = self._metadata_extractor.extract_ids(text, known_keywords)
        logger.info(
            "Bottom region keyword extraction step finished. region=%s keywords=%s",
            region_name,
            len(keyword_ids),
        )
        confidence = self._safe_confidence(ocr_data.get("confidence", 0.0))
        lines = self._safe_lines(ocr_data.get("lines", []))
        logger.info(
            "Bottom region parse finished. region=%s conf=%.3f text_len=%s lines=%s symbols=%s keywords=%s",
            region_name,
            confidence,
            len(text),
            len(lines),
            len(detected_symbols),
            len(keyword_ids),
        )

        return RegionParseResult(
            region_name=region_name,
            text=text,
            confidence=confidence,
            lines=lines,
            detected_symbols=detected_symbols,
            normalized_fields={"rules_text": text},
            extracted_keyword_ids=keyword_ids,
            debug={"expected_symbol_types": sorted(self._EXPECTED_SYMBOL_TYPES)},
        )

    def _safe_confidence(self, raw: Any) -> float:
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    def _safe_lines(self, raw: Any) -> list[dict[str, Any]]:
        return raw if isinstance(raw, list) else []
