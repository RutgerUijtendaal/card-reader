from __future__ import annotations

from pathlib import Path
from typing import Any

from settings import settings
from storage import calculate_checksum
from templates import TemplateStore

from .field_normalizer import FieldNormalizer
from .ocr_runner import OcrRunner
from .region_cropper import RegionCropper
from .types import ParsedCard


class CardParser:
    def __init__(self, template_store: TemplateStore) -> None:
        self._template_store = template_store
        self._cropper = RegionCropper()
        self._ocr_runner = OcrRunner()
        self._normalizer = FieldNormalizer()

    def parse(self, image_path: Path, template_id: str) -> ParsedCard:
        template = self._template_store.get_template(template_id)
        checksum = calculate_checksum(image_path)
        region_crops = self._cropper.crop_regions(image_path=image_path, template=template)

        if settings.save_debug_crops:
            self._cropper.write_debug_crops(
                template_id=template_id,
                checksum=checksum,
                image_path=image_path,
                region_crops=region_crops,
            )

        region_ocr = {
            region_name: self._ocr_runner.run(crop["image"])
            for region_name, crop in region_crops.items()
        }

        top_text = self._region_text(region_ocr, "top_bar")
        type_text = self._region_text(region_ocr, "type_bar")
        rules_text = self._region_text(region_ocr, "rules_text")

        normalized_fields = self._normalizer.normalize_fields(
            image_stem=image_path.stem,
            top_text=top_text,
            type_text=type_text,
            rules_text=rules_text,
        )
        confidence = self._normalizer.confidence_breakdown(
            top_confidence=self._region_confidence(region_ocr, "top_bar"),
            type_confidence=self._region_confidence(region_ocr, "type_bar"),
            rules_confidence=self._region_confidence(region_ocr, "rules_text"),
            mana_cost=normalized_fields.get("mana_cost", ""),
        )

        raw_ocr = {
            "template": template,
            "regions": {
                region_name: {
                    "bbox": {
                        "x": crop["x"],
                        "y": crop["y"],
                        "w": crop["w"],
                        "h": crop["h"],
                    },
                    "text": self._region_text(region_ocr, region_name),
                    "confidence": self._region_confidence(region_ocr, region_name),
                    "lines": self._region_lines(region_ocr, region_name),
                    "debug_crop_written": bool(settings.save_debug_crops),
                }
                for region_name, crop in region_crops.items()
            },
            "notes": "PaddleOCR region OCR",
        }

        return ParsedCard(
            checksum=checksum,
            normalized_fields=normalized_fields,
            confidence=confidence,
            raw_ocr=raw_ocr,
        )

    def _region_text(self, region_ocr: dict[str, dict[str, Any]], region_name: str) -> str:
        raw = region_ocr.get(region_name, {}).get("text", "")
        return str(raw)

    def _region_confidence(self, region_ocr: dict[str, dict[str, Any]], region_name: str) -> float:
        raw = region_ocr.get(region_name, {}).get("confidence", 0.0)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    def _region_lines(self, region_ocr: dict[str, dict[str, Any]], region_name: str) -> list[dict[str, Any]]:
        raw = region_ocr.get(region_name, {}).get("lines", [])
        return raw if isinstance(raw, list) else []
