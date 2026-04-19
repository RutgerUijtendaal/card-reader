from __future__ import annotations

from typing import Any

from models import Keyword, Symbol
from PIL import Image

from extractors import KeywordsExtractor
from parsers.ocr_runner import OcrRunner
from parsers.symbol_detector import SymbolDetector

from .types import RegionParseResult


class BottomRegionParser:
    _EXPECTED_SYMBOL_TYPES = {"rules"}

    def __init__(
        self,
        ocr_runner: OcrRunner,
        symbol_detector: SymbolDetector,
        keywords_extractor: KeywordsExtractor,
    ) -> None:
        self._ocr_runner = ocr_runner
        self._symbol_detector = symbol_detector
        self._keywords_extractor = keywords_extractor

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
        ocr_data = self._ocr_runner.run(image)
        text = str(ocr_data.get("text", ""))
        detected_symbols = self._symbol_detector.detect(
            image=image,
            symbols=symbols,
            expected_symbol_types=self._EXPECTED_SYMBOL_TYPES,
        )
        keyword_ids = self._keywords_extractor.extract_keyword_ids(text, known_keywords)

        return RegionParseResult(
            region_name=region_name,
            text=text,
            confidence=self._safe_confidence(ocr_data.get("confidence", 0.0)),
            lines=self._safe_lines(ocr_data.get("lines", [])),
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
