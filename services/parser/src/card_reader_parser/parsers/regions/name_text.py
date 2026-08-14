from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from PIL import Image

from ..ocr_runner import OcrRunner
from ..region_config import resolve_region_ocr_config

_STAR_TAIL_PATTERN = re.compile(r"\s*[★☆✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼✽✾✿]+.*$")


@dataclass(frozen=True, slots=True)
class NameOcrText:
    text: str
    confidence: float
    lines: list[dict[str, Any]]
    ocr_config: dict[str, object]
    raw_line_count: int


def read_name_ocr_text(
    *,
    ocr_runner: OcrRunner,
    image: Image.Image,
    region_spec: dict[str, Any],
) -> NameOcrText:
    ocr_config = resolve_region_ocr_config(region_spec)
    ocr_data = ocr_runner.run(image, config=ocr_config)
    lines = _safe_lines(ocr_data.get("lines", []))
    return NameOcrText(
        text="\n".join(
            str(row.get("text", "")).strip() for row in lines if row.get("text")
        ).strip(),
        confidence=_average_line_confidence(lines),
        lines=lines,
        ocr_config=ocr_config,
        raw_line_count=len(lines),
    )


def normalize_name_text(text: str) -> str:
    compact = text.replace("\n", " ").strip()
    return _STAR_TAIL_PATTERN.sub("", compact).strip()


def _safe_lines(raw: Any) -> list[dict[str, Any]]:
    return raw if isinstance(raw, list) else []


def _safe_confidence(raw: Any) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _average_line_confidence(lines: list[dict[str, Any]]) -> float:
    if not lines:
        return 0.0
    values = [_safe_confidence(row.get("confidence", 0.0)) for row in lines]
    return float(sum(values) / len(values))
