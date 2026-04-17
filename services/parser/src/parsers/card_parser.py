from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from settings import settings
from storage import calculate_checksum
from templates import TemplateStore

logger = logging.getLogger(__name__)

try:
    import numpy as np
except Exception:  # pragma: no cover - optional runtime dependency handling
    np = None  # type: ignore[assignment]

try:
    from paddleocr import PaddleOCR
except Exception:  # pragma: no cover - optional runtime dependency handling
    PaddleOCR = None  # type: ignore[assignment]


@dataclass(slots=True)
class ParsedCard:
    checksum: str
    normalized_fields: dict[str, str]
    confidence: dict[str, float]
    raw_ocr: dict[str, Any]


class CardParser:
    def __init__(self, template_store: TemplateStore) -> None:
        self._template_store = template_store
        self._ocr_engine: Any = None
        self._ocr_init_failed = False

    def parse(self, image_path: Path, template_id: str) -> ParsedCard:
        template = self._load_template(template_id)
        checksum = calculate_checksum(image_path)
        region_crops = self._crop_regions(image_path=image_path, template=template)

        if settings.save_debug_crops:
            self._write_debug_crops(
                template_id=template_id,
                checksum=checksum,
                image_path=image_path,
                region_crops=region_crops,
            )

        region_ocr = {
            region_name: self._run_ocr(crop["image"])
            for region_name, crop in region_crops.items()
        }
        top_text = region_ocr.get("top_bar", {}).get("text", "")
        type_text = region_ocr.get("type_bar", {}).get("text", "")
        rules_text = region_ocr.get("rules_text", {}).get("text", "")

        name = self._extract_name_from_top_bar(top_text) or image_path.stem
        mana_cost = self._extract_mana_hint(top_text)

        normalized_fields = {
            "name": name,
            "type_line": type_text,
            "mana_cost": mana_cost,
            "rules_text": rules_text,
        }

        name_conf = float(region_ocr.get("top_bar", {}).get("confidence", 0.0))
        type_conf = float(region_ocr.get("type_bar", {}).get("confidence", 0.0))
        rules_conf = float(region_ocr.get("rules_text", {}).get("confidence", 0.0))
        mana_conf = name_conf * 0.8 if mana_cost else 0.0

        present_conf = [value for value in (name_conf, type_conf, rules_conf, mana_conf) if value > 0.0]
        overall = float(sum(present_conf) / len(present_conf)) if present_conf else 0.0

        confidence = {
            "name": round(name_conf, 3),
            "type_line": round(type_conf, 3),
            "mana_cost": round(mana_conf, 3),
            "rules_text": round(rules_conf, 3),
            "overall": round(overall, 3),
        }
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
                    "text": region_ocr.get(region_name, {}).get("text", ""),
                    "confidence": region_ocr.get(region_name, {}).get("confidence", 0.0),
                    "lines": region_ocr.get(region_name, {}).get("lines", []),
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

    def _load_template(self, template_id: str) -> dict[str, Any]:
        return self._template_store.get_template(template_id)

    def _crop_regions(self, image_path: Path, template: dict[str, Any]) -> dict[str, dict[str, Any]]:
        regions = template.get("regions")
        if not isinstance(regions, dict) or not regions:
            raise ValueError("Template has no valid regions")

        template_width = self._as_int(template.get("card_width"))
        template_height = self._as_int(template.get("card_height"))
        region_crops: dict[str, dict[str, Any]] = {}

        with Image.open(image_path) as image:
            width, height = image.size
            for region_name, region_spec in regions.items():
                x, y, w, h = self._resolve_bbox(
                    region_spec=region_spec,
                    image_width=width,
                    image_height=height,
                    template_width=template_width,
                    template_height=template_height,
                )
                cropped = image.crop((x, y, x + w, y + h)).copy()
                region_crops[region_name] = {"x": x, "y": y, "w": w, "h": h, "image": cropped}

        return region_crops

    def _write_debug_crops(
        self,
        *,
        template_id: str,
        checksum: str,
        image_path: Path,
        region_crops: dict[str, dict[str, Any]],
    ) -> None:
        output_dir = settings.debug_crops_dir / template_id / checksum
        output_dir.mkdir(parents=True, exist_ok=True)
        for region_name, crop in region_crops.items():
            output_path = output_dir / f"{region_name}.png"
            crop_image = crop["image"]
            if isinstance(crop_image, Image.Image):
                crop_image.save(output_path)

        metadata_path = output_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps(
                {
                    "source_file": str(image_path),
                    "template_id": template_id,
                    "checksum": checksum,
                    "regions": {
                        name: {"x": crop["x"], "y": crop["y"], "w": crop["w"], "h": crop["h"]}
                        for name, crop in region_crops.items()
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _run_ocr(self, image: Image.Image) -> dict[str, Any]:
        engine = self._get_ocr_engine()
        if engine is None or np is None:
            return {"text": "", "confidence": 0.0, "lines": []}

        try:
            image_rgb = image.convert("RGB")
            image_np = np.asarray(image_rgb)
            prediction = list(engine.predict(image_np))
        except Exception:
            logger.exception("OCR execution failed")
            return {"text": "", "confidence": 0.0, "lines": []}

        if not prediction:
            return {"text": "", "confidence": 0.0, "lines": []}

        first = prediction[0]
        json_payload = getattr(first, "json", None)
        if not isinstance(json_payload, dict):
            return {"text": "", "confidence": 0.0, "lines": []}

        lines_data: list[dict[str, Any]] = []
        confidences: list[float] = []
        texts: list[str] = []

        for text_value, conf_value in self._extract_text_conf_pairs(json_payload):
            if not text_value:
                continue
            texts.append(text_value)
            confidences.append(conf_value)
            lines_data.append({"text": text_value, "confidence": conf_value})

        combined = "\n".join(texts).strip()
        avg_conf = float(sum(confidences) / len(confidences)) if confidences else 0.0
        return {"text": combined, "confidence": avg_conf, "lines": lines_data}

    def _extract_text_conf_pairs(self, result_json: Any) -> list[tuple[str, float]]:
        # PaddleOCR 3.x predict result JSON shape:
        # { "res": { "rec_texts": [...], "rec_scores": [...] } }
        if not isinstance(result_json, dict):
            return []

        payload = result_json.get("res")
        if not isinstance(payload, dict):
            return []

        rec_texts = payload.get("rec_texts")
        rec_scores = payload.get("rec_scores")
        if rec_texts is None or rec_scores is None:
            return []

        if not isinstance(rec_texts, list):
            return []

        try:
            score_values = list(rec_scores)
        except TypeError:
            return []

        pairs: list[tuple[str, float]] = []
        for text_item, score_item in zip(rec_texts, score_values):
            text_value = str(text_item).strip()
            if not text_value:
                continue
            try:
                conf_value = float(score_item)
            except (TypeError, ValueError):
                continue
            pairs.append((text_value, conf_value))
        return pairs

    def _get_ocr_engine(self) -> Any:
        if self._ocr_engine is not None:
            return self._ocr_engine
        if self._ocr_init_failed:
            return None
        if PaddleOCR is None or np is None:
            logger.warning("PaddleOCR or numpy not available. OCR disabled.")
            self._ocr_init_failed = True
            return None

        try:
            self._ocr_engine = PaddleOCR(
                lang="en",
                device="cpu",
                enable_mkldnn=False,
            )
        except Exception:
            logger.exception("Failed to initialize PaddleOCR")
            self._ocr_init_failed = True
            self._ocr_engine = None
        return self._ocr_engine

    def _extract_name_from_top_bar(self, top_bar_text: str) -> str:
        text = top_bar_text.replace("\n", " ").strip()
        if not text:
            return ""
        text = re.sub(r"\s+\d+\s*$", "", text)
        text = re.sub(r"\s*[★☆✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼✽✾✿]+.*$", "", text)
        return text.strip()

    def _extract_mana_hint(self, top_bar_text: str) -> str:
        text = top_bar_text.replace("\n", " ").strip()
        if not text:
            return ""
        match = re.search(r"(\d+(?:\s*[★☆✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼✽✾✿xX]*)?)$", text)
        if not match:
            return ""
        return match.group(1).strip()

    def _resolve_bbox(
        self,
        *,
        region_spec: Any,
        image_width: int,
        image_height: int,
        template_width: int | None,
        template_height: int | None,
    ) -> tuple[int, int, int, int]:
        if isinstance(region_spec, dict):
            return self._resolve_bbox_from_object(
                region_spec=region_spec,
                image_width=image_width,
                image_height=image_height,
            )

        if isinstance(region_spec, list) and len(region_spec) == 4:
            x = self._as_int(region_spec[0]) or 0
            y = self._as_int(region_spec[1]) or 0
            w = self._as_int(region_spec[2]) or image_width
            h = self._as_int(region_spec[3]) or image_height
            if template_width and template_height:
                x = int(round((x / template_width) * image_width))
                y = int(round((y / template_height) * image_height))
                w = int(round((w / template_width) * image_width))
                h = int(round((h / template_height) * image_height))
            return self._clamp_bbox(x=x, y=y, w=w, h=h, image_width=image_width, image_height=image_height)

        raise ValueError("Invalid region specification. Expected object or [x,y,w,h] list.")

    def _resolve_bbox_from_object(
        self,
        *,
        region_spec: dict[str, Any],
        image_width: int,
        image_height: int,
    ) -> tuple[int, int, int, int]:
        unit = str(region_spec.get("unit", "relative")).lower()
        x_raw = float(region_spec.get("x", 0.0))
        y_raw = float(region_spec.get("y", 0.0))
        w_raw = float(region_spec.get("w", 1.0))
        h_raw = float(region_spec.get("h", 1.0))

        if unit == "relative":
            x = int(round(x_raw * image_width))
            y = int(round(y_raw * image_height))
            w = int(round(w_raw * image_width))
            h = int(round(h_raw * image_height))
            return self._clamp_bbox(x=x, y=y, w=w, h=h, image_width=image_width, image_height=image_height)

        if unit == "absolute":
            return self._clamp_bbox(
                x=int(round(x_raw)),
                y=int(round(y_raw)),
                w=int(round(w_raw)),
                h=int(round(h_raw)),
                image_width=image_width,
                image_height=image_height,
            )

        raise ValueError(f"Unsupported region unit '{unit}'.")

    def _clamp_bbox(
        self,
        *,
        x: int,
        y: int,
        w: int,
        h: int,
        image_width: int,
        image_height: int,
    ) -> tuple[int, int, int, int]:
        x = max(0, min(x, image_width - 1))
        y = max(0, min(y, image_height - 1))
        w = max(1, min(w, image_width - x))
        h = max(1, min(h, image_height - y))
        return x, y, w, h

    def _as_int(self, value: Any) -> int | None:
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(round(value))
        return None

