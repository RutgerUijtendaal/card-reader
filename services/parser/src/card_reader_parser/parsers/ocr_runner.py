from __future__ import annotations

import logging
from typing import Any, TypedDict

from PIL import Image

logger = logging.getLogger(__name__)

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore[assignment]

try:
    from paddleocr import PaddleOCR  # type: ignore[import-untyped]
except Exception:  # pragma: no cover
    PaddleOCR = None

_PADDLEX_OCR_CONFIG: dict[str, Any] = {
    "pipeline_name": "OCR",
    "text_type": "general",
    "use_doc_preprocessor": False,
    "use_textline_orientation": False,
    "SubModules": {
        "TextDetection": {
            "module_name": "text_detection",
            "model_name": "PP-OCRv5_server_det",
            "model_dir": None,
            "limit_side_len": 512,
            "limit_type": "max",
            "max_side_limit": 1024,
            "thresh": 0.3,
            "box_thresh": 0.6,
            "unclip_ratio": 1.5,
        },
        "TextRecognition": {
            "module_name": "text_recognition",
            "model_name": "PP-OCRv5_server_rec",
            "model_dir": None,
            "batch_size": 1,
            "score_thresh": 0.0,
        },
    },
}


Point = tuple[float, float]
Polygon = list[Point]


class OcrLineItem(TypedDict):
    text: str
    confidence: float
    x: float
    y: float
    box: Polygon


class OcrRunner:
    def __init__(self) -> None:
        self._ocr_engine: Any = None
        self._ocr_init_failed = False

    def run(self, image: Image.Image) -> dict[str, Any]:
        logger.info("OCR run started. image_size=%sx%s", image.width, image.height)
        engine = self._get_ocr_engine()
        if engine is None or np is None:
            logger.warning("OCR run skipped. engine_available=%s numpy_available=%s", engine is not None, np is not None)
            return {"text": "", "confidence": 0.0, "lines": []}

        try:
            image_rgb = image.convert("RGB")
            image_np = np.asarray(image_rgb)
            prediction = list(engine.predict(image_np))
            logger.info("OCR run step: engine.predict returned. predictions=%s", len(prediction))
        except Exception:
            logger.exception("OCR execution failed")
            return {"text": "", "confidence": 0.0, "lines": []}

        if not prediction:
            logger.info("OCR run finished with empty prediction.")
            return {"text": "", "confidence": 0.0, "lines": []}

        first = prediction[0]
        json_payload = getattr(first, "json", None)
        if not isinstance(json_payload, dict):
            logger.warning("OCR run finished with non-dict payload.")
            return {"text": "", "confidence": 0.0, "lines": []}
        return self._finalize_from_json_payload(json_payload)

    def _finalize_from_json_payload(self, json_payload: dict[str, Any]) -> dict[str, Any]:
        lines_data: list[OcrLineItem] = []
        confidences: list[float] = []

        for poly, text_value, conf_value in self._extract_text_conf_pairs(json_payload):
            if not text_value:
                continue

            # compute a simple center point
            ys = [p[1] for p in poly]
            xs = [p[0] for p in poly]

            lines_data.append({
                "text": text_value,
                "confidence": conf_value,
                "x": sum(xs) / len(xs),
                "y": sum(ys) / len(ys),
                "box": poly,
            })
            confidences.append(conf_value)

        grouped_lines = self._group_by_lines(lines_data)
        final_lines: list[str] = []
        for line in grouped_lines:
            line = sorted(line, key=lambda x: x["x"])
            final_lines.append(" ".join([w["text"] for w in line]))

        combined = "\n".join(final_lines).strip()
        avg_conf = float(sum(confidences) / len(confidences)) if confidences else 0.0
        logger.info(
            "OCR run finished. text_len=%s lines=%s avg_conf=%.3f",
            len(combined),
            len(lines_data),
            avg_conf,
        )
        return {"text": combined, "confidence": avg_conf, "lines": lines_data}


    def _group_by_lines(
        self,
        items: list[OcrLineItem],
        y_threshold: float = 12,
    ) -> list[list[OcrLineItem]]:
        # sort top → bottom
        sorted_items = sorted(items, key=lambda x: x["y"])

        lines: list[list[OcrLineItem]] = []
        current_line: list[OcrLineItem] = []

        for item in sorted_items:
            if not current_line:
                current_line.append(item)
                continue

            # compare with last item in current line
            if abs(item["y"] - current_line[-1]["y"]) < y_threshold:
                current_line.append(item)
            else:
                lines.append(current_line)
                current_line = [item]

        if current_line:
            lines.append(current_line)

        return lines

    def _extract_text_conf_pairs(self, result_json: Any) -> list[tuple[Polygon, str, float]]:
        if not isinstance(result_json, dict):
            return []

        payload = result_json.get("res")
        if not isinstance(payload, dict):
            return []

        rec_texts = payload.get("rec_texts")
        rec_scores = payload.get("rec_scores")
        rec_polys = payload.get("rec_polys")

        if not (isinstance(rec_texts, list) and isinstance(rec_scores, list) and isinstance(rec_polys, list)):
            return []

        pairs: list[tuple[Polygon, str, float]] = []

        for text_item, score_item, poly in zip(rec_texts, rec_scores, rec_polys):
            text_value = str(text_item).strip()
            if not text_value:
                continue

            try:
                conf_value = float(score_item)
            except (TypeError, ValueError):
                continue

            if not isinstance(poly, list):
                continue

            normalized_poly: Polygon = []
            valid_poly = True
            for point in poly:
                if not isinstance(point, (list, tuple)) or len(point) < 2:
                    valid_poly = False
                    break
                try:
                    px = float(point[0])
                    py = float(point[1])
                except (TypeError, ValueError):
                    valid_poly = False
                    break
                normalized_poly.append((px, py))

            if not valid_poly or not normalized_poly:
                continue

            pairs.append((normalized_poly, text_value, conf_value))

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
                paddlex_config=_PADDLEX_OCR_CONFIG,
            )
        except Exception:
            logger.exception("Failed to initialize PaddleOCR")
            self._ocr_init_failed = True
            self._ocr_engine = None
        return self._ocr_engine
