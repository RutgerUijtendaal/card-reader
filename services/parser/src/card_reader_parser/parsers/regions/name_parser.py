from __future__ import annotations

import logging
from typing import Any

from PIL import Image

from ..ocr_runner import OcrRunner
from .name_text import normalize_name_text, read_name_ocr_text
from .types import RegionParseResult

logger = logging.getLogger(__name__)


class NameParser:
    def __init__(self, ocr_runner: OcrRunner) -> None:
        self._ocr_runner = ocr_runner

    def parse(
        self,
        *,
        region_name: str,
        image: Image.Image,
        image_stem: str,
        region_spec: dict[str, Any],
    ) -> RegionParseResult:
        logger.info(
            "Name parser started. region=%s image_size=%sx%s",
            region_name,
            image.width,
            image.height,
        )
        ocr_text = read_name_ocr_text(
            ocr_runner=self._ocr_runner,
            image=image,
            region_spec=region_spec,
        )
        name = normalize_name_text(ocr_text.text) or image_stem
        logger.info(
            "Name parser finished. region=%s conf=%.3f name=%r",
            region_name,
            ocr_text.confidence,
            name,
        )
        return RegionParseResult(
            region_name=region_name,
            text=ocr_text.text,
            confidence=ocr_text.confidence,
            lines=ocr_text.lines,
            normalized_fields={"name": name},
            debug={
                "full_ocr_text": ocr_text.text,
                "ocr_config": ocr_text.ocr_config,
                "ocr_line_count_raw": ocr_text.raw_line_count,
                "ocr_line_count_filtered": len(ocr_text.lines),
            },
        )
