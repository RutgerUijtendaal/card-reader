from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from card_reader_core.models import Symbol
from card_reader_core.settings import settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DetectionBBox:
    x: int
    y: int
    w: int
    h: int


@dataclass(slots=True)
class DetectedSymbol:
    symbol_id: str
    key: str
    symbol_type: str
    confidence: float
    bbox: DetectionBBox
    detector_type: str
    match_metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["bbox"] = asdict(self.bbox)
        return out


@dataclass(slots=True)
class TemplateDetectorConfig:
    threshold: float = 0.8
    scales: tuple[float, ...] = (1.0,)
    max_candidates_per_asset: int = 40
    max_detections_per_symbol: int = 8
    nms_iou_threshold: float = 0.25
    center_crop_ratio: float = 0.70
    method: int = cv2.TM_CCOEFF_NORMED


class SymbolDetector:
    def detect(
        self,
        image: Image.Image | np.ndarray,
        symbols: list[Symbol],
        expected_symbol_types: set[str] | None = None,
    ) -> list[DetectedSymbol]:
        logger.info(
            "Symbol detector started. symbol_candidates=%s expected_types=%s",
            len(symbols),
            sorted(expected_symbol_types) if expected_symbol_types is not None else None,
        )
        if not symbols:
            logger.info("Symbol detector finished early (no symbols).")
            return []

        image_gray = self._to_gray_numpy(image)
        height, width = image_gray.shape[:2]
        if height == 0 or width == 0:
            logger.warning("Symbol detector finished early (empty image).")
            return []

        detections: list[DetectedSymbol] = []
        for symbol in symbols:
            if symbol.detector_type != "template":
                continue
            if (
                expected_symbol_types is not None
                and symbol.symbol_type.strip().lower() not in expected_symbol_types
            ):
                continue
            config = self._parse_config(symbol.detection_config_json)
            template_assets = self._resolve_template_assets(symbol.reference_assets_json)
            if not template_assets:
                continue

            symbol_matches: list[DetectedSymbol] = []
            symbol_best_score = 0.0
            for asset_path in template_assets:
                template_gray = self._load_template(asset_path, config.center_crop_ratio)
                if template_gray is None:
                    continue
                asset_matches, asset_best_score = self._match_template(
                    image_gray=image_gray,
                    symbol=symbol,
                    template_gray=template_gray,
                    template_path=asset_path,
                    config=config,
                )
                symbol_matches.extend(asset_matches)
                symbol_best_score = max(symbol_best_score, asset_best_score)

            symbol_matches = self._nms(symbol_matches, config.nms_iou_threshold)
            symbol_matches.sort(key=lambda row: row.confidence, reverse=True)
            logger.info(
                "Symbol detector summary. key=%s symbol_type=%s assets=%s matches=%s best_score=%.4f threshold=%.4f",
                symbol.key,
                symbol.symbol_type,
                len(template_assets),
                len(symbol_matches),
                symbol_best_score,
                config.threshold,
            )
            detections.extend(symbol_matches[: config.max_detections_per_symbol])

        detections.sort(key=lambda row: row.confidence, reverse=True)
        logger.info(
            "Symbol detector finished. detections=%s",
            len(detections),
        )
        return detections

    def _to_gray_numpy(self, image: Image.Image | np.ndarray) -> np.ndarray:
        if isinstance(image, Image.Image):
            return np.array(image.convert("L"))

        if image.ndim == 2:
            return image.astype(np.uint8)
        if image.ndim == 3 and image.shape[2] == 3:
            return cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_RGB2GRAY)
        if image.ndim == 3 and image.shape[2] == 4:
            return cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_RGBA2GRAY)

        raise ValueError("Unsupported image shape for symbol detection")

    def _parse_config(self, raw: object) -> TemplateDetectorConfig:
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                return TemplateDetectorConfig()
        if not isinstance(raw, dict):
            return TemplateDetectorConfig()
        data = raw

        threshold = self._clamp_float(data.get("threshold"), 0.0, 1.0, 0.9)
        scales = self._parse_scales(data.get("scales"))
        max_candidates_per_asset = self._to_positive_int(data.get("max_candidates_per_asset"), 40)
        max_detections_per_symbol = self._to_positive_int(data.get("max_detections_per_symbol"), 8)
        nms_iou_threshold = self._clamp_float(data.get("nms_iou_threshold"), 0.0, 1.0, 0.25)
        center_crop_ratio = self._clamp_float(data.get("center_crop_ratio"), 0.0, 1.0, 0.70)
        return TemplateDetectorConfig(
            threshold=threshold,
            scales=scales,
            max_candidates_per_asset=max_candidates_per_asset,
            max_detections_per_symbol=max_detections_per_symbol,
            nms_iou_threshold=nms_iou_threshold,
            center_crop_ratio=center_crop_ratio,
        )

    def _resolve_template_assets(self, raw: object) -> list[Path]:
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                return []
        if not isinstance(raw, list):
            return []

        out: list[Path] = []
        symbols_root = settings.storage_root_dir / "symbols"
        for item in raw:
            if not isinstance(item, str):
                continue
            value = item.strip()
            if not value:
                continue
            path = Path(value)
            if not path.is_absolute():
                path = symbols_root / path
            if path.exists() and path.is_file():
                out.append(path)
        return out

    def _load_template(self, path: Path, center_crop_ratio: float) -> np.ndarray | None:
        image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            return None
        return self._center_crop_template(image, center_crop_ratio)

    def _center_crop_template(self, image: np.ndarray, ratio: float) -> np.ndarray:
        if ratio <= 0.0 or ratio >= 1.0:
            return image

        height, width = image.shape[:2]
        if width < 6 or height < 6:
            return image

        crop_w = max(3, int(round(width * ratio)))
        crop_h = max(3, int(round(height * ratio)))
        crop_w = min(crop_w, width)
        crop_h = min(crop_h, height)

        x1 = max(0, (width - crop_w) // 2)
        y1 = max(0, (height - crop_h) // 2)
        x2 = min(width, x1 + crop_w)
        y2 = min(height, y1 + crop_h)

        cropped = image[y1:y2, x1:x2]
        if cropped.size == 0:
            return image
        return cropped

    def _match_template(
        self,
        *,
        image_gray: np.ndarray,
        symbol: Symbol,
        template_gray: np.ndarray,
        template_path: Path,
        config: TemplateDetectorConfig,
    ) -> tuple[list[DetectedSymbol], float]:
        image_h, image_w = image_gray.shape[:2]
        matches: list[DetectedSymbol] = []
        best_score = 0.0

        for scale in config.scales:
            scaled_template = self._scaled_template(template_gray, scale)
            if scaled_template is None:
                continue

            th, tw = scaled_template.shape[:2]
            if th > image_h or tw > image_w:
                continue

            result = cv2.matchTemplate(image_gray, scaled_template, config.method)
            try:
                best_score = max(best_score, float(result.max()))
            except Exception:
                pass
            ys, xs = np.where(result >= config.threshold)
            if len(xs) == 0:
                continue

            scored: list[tuple[float, int, int]] = [
                (float(result[y, x]), int(x), int(y)) for x, y in zip(xs.tolist(), ys.tolist(), strict=False)
            ]
            scored.sort(key=lambda row: row[0], reverse=True)
            limited = scored[: config.max_candidates_per_asset]

            for confidence, x, y in limited:
                matches.append(
                    DetectedSymbol(
                        symbol_id=symbol.id,
                        key=symbol.key,
                        symbol_type=symbol.symbol_type,
                        confidence=round(confidence, 4),
                        bbox=DetectionBBox(x=x, y=y, w=tw, h=th),
                        detector_type="template",
                        match_metadata={
                            "scale": scale,
                            "text_token": symbol.text_token,
                            "template_path": str(template_path),
                            "template_width": tw,
                            "template_height": th,
                        },
                    )
                )

        return matches, best_score

    def _scaled_template(self, template: np.ndarray, scale: float) -> np.ndarray | None:
        if abs(scale - 1.0) < 1e-6:
            return template
        width = max(1, int(round(template.shape[1] * scale)))
        height = max(1, int(round(template.shape[0] * scale)))
        if width < 3 or height < 3:
            return None
        return cv2.resize(template, (width, height), interpolation=cv2.INTER_AREA)

    def _nms(self, rows: list[DetectedSymbol], iou_threshold: float) -> list[DetectedSymbol]:
        if not rows:
            return []
        rows = sorted(rows, key=lambda row: row.confidence, reverse=True)
        selected: list[DetectedSymbol] = []
        for candidate in rows:
            if all(self._bbox_iou(candidate.bbox, keep.bbox) <= iou_threshold for keep in selected):
                selected.append(candidate)
        return selected

    def _bbox_iou(self, a: DetectionBBox, b: DetectionBBox) -> float:
        ax2, ay2 = a.x + a.w, a.y + a.h
        bx2, by2 = b.x + b.w, b.y + b.h
        inter_x1 = max(a.x, b.x)
        inter_y1 = max(a.y, b.y)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h
        if inter_area == 0:
            return 0.0
        area_a = a.w * a.h
        area_b = b.w * b.h
        union = max(1, area_a + area_b - inter_area)
        return inter_area / union

    def _parse_scales(self, value: object) -> tuple[float, ...]:
        if not isinstance(value, list):
            return (1.0,)
        out: list[float] = []
        for item in value:
            if isinstance(item, (int, float)):
                scale = float(item)
                if 0.2 <= scale <= 4.0:
                    out.append(scale)
        return tuple(out) if out else (1.0,)

    def _clamp_float(self, value: object, lower: float, upper: float, default: float) -> float:
        if isinstance(value, (int, float)):
            raw = float(value)
            return max(lower, min(raw, upper))
        return default

    def _to_positive_int(self, value: object, default: int) -> int:
        if isinstance(value, int) and value > 0:
            return value
        if isinstance(value, float) and value > 0:
            return int(round(value))
        return default

