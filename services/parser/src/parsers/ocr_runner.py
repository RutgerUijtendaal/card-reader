from __future__ import annotations

import logging
from typing import Any

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
            "limit_side_len": 64,
            "limit_type": "min",
            "max_side_limit": 4000,
            "thresh": 0.3,
            "box_thresh": 0.6,
            "unclip_ratio": 1.5,
        },
        "TextRecognition": {
            "module_name": "text_recognition",
            "model_name": "PP-OCRv5_server_rec",
            "model_dir": None,
            "batch_size": 6,
            "score_thresh": 0.0,
        },
    },
}


class OcrRunner:
    def __init__(self) -> None:
        self._ocr_engine: Any = None
        self._ocr_init_failed = False

    def run(self, image: Image.Image) -> dict[str, Any]:
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
                paddlex_config=_PADDLEX_OCR_CONFIG,
            )
        except Exception:
            logger.exception("Failed to initialize PaddleOCR")
            self._ocr_init_failed = True
            self._ocr_engine = None
        return self._ocr_engine
