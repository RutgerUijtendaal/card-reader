from __future__ import annotations

import logging
from typing import Any

from card_reader_core.models import Keyword, Symbol
from PIL import Image

from ...extractors import KnownMetadataExtractor
from ..rule_text import RuleTextEnricher
from ..ocr_runner import OcrRunner
from ..region_config import resolve_region_ocr_config
from ..symbol_detector import SymbolDetector

from .types import RegionParseResult

logger = logging.getLogger(__name__)


class RulesTextParser:
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
        self._rule_text_enricher = RuleTextEnricher()

    def parse(
        self,
        *,
        region_name: str,
        image: Image.Image,
        region_spec: dict[str, Any],
        symbols: list[Symbol],
        known_keywords: list[Keyword],
    ) -> RegionParseResult:
        logger.info("Rules text parser started. region=%s image_size=%sx%s", region_name, image.width, image.height)
        logger.info("Rules text parser OCR step started. region=%s", region_name)
        ocr_data = self._ocr_runner.run(image, config=resolve_region_ocr_config(region_spec))
        logger.info(
            "Rules text parser OCR step finished. region=%s conf=%.3f",
            region_name,
            self._safe_confidence(ocr_data.get("confidence", 0.0)),
        )
        raw_text = str(ocr_data.get("text", ""))
        logger.info(
            "Rules text parser symbol detection step started. region=%s symbol_candidates=%s expected_types=%s",
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
            "Rules text parser symbol detection step finished. region=%s symbols=%s",
            region_name,
            len(detected_symbols),
        )
        logger.info(
            "Rules text parser enrichment step started. text=%s symbols=%s",
            raw_text,
            len(detected_symbols),
        )
        enrichment = self._rule_text_enricher.enrich(
            raw_text=raw_text,
            detected_symbols=detected_symbols,
            symbols=symbols,
        )
        logger.info(
            "Rules text parser enrichment step finished. text=%s symbols=%s",
            raw_text,
            len(detected_symbols),
        )
        logger.info(
            "Rules text parser keyword extraction step started. region=%s known_keywords=%s",
            region_name,
            len(known_keywords),
        )
        keyword_ids = self._metadata_extractor.extract_ids(enrichment.cleaned_text, known_keywords)
        logger.info(
            "Rules text parser keyword extraction step finished. region=%s keywords=%s",
            region_name,
            len(keyword_ids),
        )
        confidence = self._safe_confidence(ocr_data.get("confidence", 0.0))
        lines = self._safe_lines(ocr_data.get("lines", []))
        logger.info(
            "Rules text parser finished. region=%s conf=%.3f text_len=%s lines=%s symbols=%s keywords=%s",
            region_name,
            confidence,
            len(enrichment.rendered_text),
            len(lines),
            len(detected_symbols),
            len(keyword_ids),
        )

        return RegionParseResult(
            region_name=region_name,
            text=enrichment.rendered_text,
            confidence=confidence,
            lines=lines,
            detected_symbols=detected_symbols,
            normalized_fields={
                "rules_text_raw": enrichment.raw_text,
                "rules_text_enriched": enrichment.enriched_text,
                "rules_text": enrichment.rendered_text,
            },
            extracted_keyword_ids=keyword_ids,
            debug={
                "expected_symbol_types": sorted(self._EXPECTED_SYMBOL_TYPES),
                "rule_text_enrichment": enrichment.debug,
            },
        )

    def _safe_confidence(self, raw: Any) -> float:
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    def _safe_lines(self, raw: Any) -> list[dict[str, Any]]:
        return raw if isinstance(raw, list) else []
