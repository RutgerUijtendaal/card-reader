from __future__ import annotations

import logging
import re
from typing import Any

from PIL import Image
from PIL import ImageOps

from ..ocr_runner import OcrRunner

from .types import RegionParseResult

logger = logging.getLogger(__name__)


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
        logger.info(
            "Stats region parse started. region=%s field=%s image_size=%sx%s",
            region_name,
            field_name,
            image.width,
            image.height,
        )
        attempts = self._build_ocr_attempts()

        chosen_ocr_data: dict[str, Any] | None = None
        chosen_text = ""
        value: int | None = None

        for attempt_scale, attempt_grayscale in attempts:
            logger.info(
                "Stats OCR attempt. region=%s field=%s scale=%.2f grayscale=%s",
                region_name,
                field_name,
                attempt_scale,
                attempt_grayscale,
            )
            preprocessed_image = self._preprocess_image(
                image,
                scale=attempt_scale,
                grayscale=attempt_grayscale,
            )
            ocr_data = self._ocr_runner.run(preprocessed_image)
            text = str(ocr_data.get("text", ""))
            parsed_value = self._extract_number(text)
            logger.info(
                "Stats OCR attempt result. region=%s field=%s text=%r parsed_value=%s conf=%.3f",
                region_name,
                field_name,
                text,
                parsed_value,
                self._safe_confidence(ocr_data.get("confidence", 0.0)),
            )

            if chosen_ocr_data is None:
                chosen_ocr_data = ocr_data
                chosen_text = text
            if parsed_value is not None:
                chosen_ocr_data = ocr_data
                chosen_text = text
                value = parsed_value
                break

        if chosen_ocr_data is None:
            chosen_ocr_data = {"text": "", "confidence": 0.0, "lines": []}

        normalized_fields: dict[str, str] = {}
        if value is not None:
            normalized_fields[field_name] = str(value)
        logger.info(
            "Stats region parse finished. region=%s field=%s value=%s conf=%.3f",
            region_name,
            field_name,
            value,
            self._safe_confidence(chosen_ocr_data.get("confidence", 0.0)),
        )

        return RegionParseResult(
            region_name=region_name,
            text=chosen_text,
            confidence=self._safe_confidence(chosen_ocr_data.get("confidence", 0.0)),
            lines=self._safe_lines(chosen_ocr_data.get("lines", [])),
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

    def _scale_image(self, image: Image.Image, scale: float) -> Image.Image:
        width, height = image.size
        target_width = max(1, int(width * scale))
        target_height = max(1, int(height * scale))
        return image.resize((target_width, target_height), Image.Resampling.LANCZOS)

    def _preprocess_image(self, image: Image.Image, *, scale: float, grayscale: bool) -> Image.Image:
        out = self._scale_image(image, scale)
        if grayscale:
            out = ImageOps.grayscale(out)
        return out

    def _build_ocr_attempts(self) -> list[tuple[float, bool]]:
        # Always apply scaling + grayscale preprocessing for stat OCR.
        candidates: list[tuple[float, bool]] = [
            (0.5, True),
            (1.0, True),
            (2.0, True),
            (3.0, True),
        ]
        out: list[tuple[float, bool]] = []
        seen: set[tuple[float, bool]] = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            out.append(candidate)
        return out

