from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from card_reader_api.infrastructure.storage import calculate_checksum


@dataclass(slots=True)
class ParsedCard:
    checksum: str
    normalized_fields: dict[str, str]
    confidence: dict[str, float]
    raw_ocr: dict[str, Any]


class CardParser:
    def __init__(self, templates_dir: Path) -> None:
        self._templates_dir = templates_dir

    def parse(self, image_path: Path, template_id: str) -> ParsedCard:
        template = self._load_template(template_id)
        checksum = calculate_checksum(image_path)

        # Placeholder OCR pipeline hooks. Real implementation will run region-specific
        # preprocessing with OpenCV + PaddleOCR using template anchors and crops.
        normalized_fields = {
            "name": image_path.stem,
            "type_line": "Unknown Type",
            "mana_cost": "{1}",
            "rules_text": "OCR pending",
        }
        confidence = {
            "name": 0.95,
            "type_line": 0.55,
            "mana_cost": 0.4,
            "rules_text": 0.25,
            "overall": 0.54,
        }
        raw_ocr = {
            "template": template,
            "regions": {},
            "notes": "Scaffold adapter for PaddleOCR integration",
        }
        return ParsedCard(
            checksum=checksum,
            normalized_fields=normalized_fields,
            confidence=confidence,
            raw_ocr=raw_ocr,
        )

    def _load_template(self, template_id: str) -> dict[str, Any]:
        template_file = self._templates_dir / f"{template_id}.json"
        if not template_file.exists():
            raise FileNotFoundError(f"Template '{template_id}' does not exist")
        return json.loads(template_file.read_text(encoding="utf-8"))