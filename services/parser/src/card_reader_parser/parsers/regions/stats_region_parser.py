from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from PIL import Image
from PIL import ImageOps

from ..ocr_runner import OcrRunner
from ..region_config import resolve_region_ocr_config

from .types import RegionParseResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StatsOcrAttempt:
    scale: float
    grayscale: bool
    pad: int = 0
    autocontrast: bool = False
    threshold: int | None = None


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
        logger.info(
            "Stats region parse started. region=%s field=%s image_size=%sx%s",
            region_name,
            field_name,
            image.width,
            image.height,
        )
        attempts = self._build_ocr_attempts()
        ocr_config = resolve_region_ocr_config(region_spec)

        chosen_ocr_data: dict[str, Any] | None = None
        chosen_text = ""
        value: int | None = None

        for attempt in attempts:
            logger.info(
                "Stats OCR attempt. region=%s field=%s scale=%.2f grayscale=%s pad=%s autocontrast=%s threshold=%s",
                region_name,
                field_name,
                attempt.scale,
                attempt.grayscale,
                attempt.pad,
                attempt.autocontrast,
                attempt.threshold,
            )
            preprocessed_image = self._preprocess_image(
                image,
                attempt=attempt,
            )
            ocr_data = self._ocr_runner.run(preprocessed_image, config=ocr_config)
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

    def _preprocess_image(self, image: Image.Image, *, attempt: StatsOcrAttempt) -> Image.Image:
        out = image if image.mode in {"RGB", "L"} else image.convert("RGB")
        if attempt.pad > 0:
            out = ImageOps.expand(out, border=attempt.pad, fill="white")
        out = self._scale_image(out, attempt.scale)
        if attempt.autocontrast:
            out = ImageOps.autocontrast(out)
        if attempt.grayscale:
            out = ImageOps.grayscale(out)
        if attempt.threshold is not None:
            grayscale = out if out.mode == "L" else ImageOps.grayscale(out)
            out = grayscale.point(lambda value: 255 if value >= attempt.threshold else 0)
        return out

    def _build_ocr_attempts(self) -> list[StatsOcrAttempt]:
        candidates: list[StatsOcrAttempt] = [
            StatsOcrAttempt(scale=1.0, grayscale=False),
            StatsOcrAttempt(scale=1.0, grayscale=True),
            StatsOcrAttempt(scale=2.0, grayscale=False),
            StatsOcrAttempt(scale=2.0, grayscale=True),
            StatsOcrAttempt(scale=3.0, grayscale=True),
            StatsOcrAttempt(scale=4.0, grayscale=False, pad=8),
            StatsOcrAttempt(scale=4.0, grayscale=True, pad=8),
            StatsOcrAttempt(scale=4.0, grayscale=True, pad=8, autocontrast=True),
            StatsOcrAttempt(scale=5.0, grayscale=True, pad=8, autocontrast=True),
            StatsOcrAttempt(scale=5.0, grayscale=True, pad=8, autocontrast=True, threshold=180),
            StatsOcrAttempt(scale=5.0, grayscale=True, pad=8, autocontrast=True, threshold=200),
        ]
        out: list[StatsOcrAttempt] = []
        seen: set[StatsOcrAttempt] = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            out.append(candidate)
        return out
