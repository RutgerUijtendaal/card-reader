from __future__ import annotations

import logging
from typing import Any

from card_reader_core.models import Symbol
from PIL import Image

from ..symbol_detector import SymbolDetector

from .types import RegionParseResult

logger = logging.getLogger(__name__)


class AffinityRegionParser:
    _EXPECTED_SYMBOL_TYPES = {"affinity"}

    def __init__(self, symbol_detector: SymbolDetector) -> None:
        self._symbol_detector = symbol_detector

    def parse(
        self,
        *,
        region_name: str,
        image: Image.Image,
        region_spec: dict[str, Any],
        symbols: list[Symbol],
    ) -> RegionParseResult:
        _ = region_spec
        logger.info(
            "Affinity region parse started. region=%s image_size=%sx%s expected_symbol_types=%s",
            region_name,
            image.width,
            image.height,
            sorted(self._EXPECTED_SYMBOL_TYPES),
        )
        detected_symbols = self._symbol_detector.detect(
            image=image,
            symbols=symbols,
            expected_symbol_types=self._EXPECTED_SYMBOL_TYPES,
        )
        affinity_keys = [row.key for row in sorted(detected_symbols, key=lambda row: row.bbox.x)]
        logger.info(
            "Affinity region parse finished. region=%s symbols=%s affinity_keys=%s",
            region_name,
            len(detected_symbols),
            affinity_keys,
        )

        return RegionParseResult(
            region_name=region_name,
            detected_symbols=detected_symbols,
            normalized_fields={"affinity_symbols": " ".join(affinity_keys).strip()},
            debug={"expected_symbol_types": sorted(self._EXPECTED_SYMBOL_TYPES)},
        )


