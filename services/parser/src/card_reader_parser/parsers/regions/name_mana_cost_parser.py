from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Literal

from card_reader_core.models import (
    EVIL_CARD_POOL,
    NEUTRAL_CARD_POOL,
    PLAYER_CARD_POOL,
    CardPool,
    Symbol,
)
from card_reader_core.services.templates import (
    MAX_MANA_BADGE_OCR_ATTEMPTS,
    MAX_MANA_BADGE_OCR_SCALE,
)
from PIL import Image

from ..ocr_runner import OcrRunner
from ..symbol_detector import DetectedSymbol, SymbolDetector

from .name_text import normalize_name_text, read_name_ocr_text
from .types import RegionParseResult

logger = logging.getLogger(__name__)

ManaCostSource = Literal["symbols", "trailing_ocr_integer", "none"]
_MANA_COST_SOURCE_BY_POOL: dict[CardPool, ManaCostSource] = {
    PLAYER_CARD_POOL: "symbols",
    EVIL_CARD_POOL: "trailing_ocr_integer",
    NEUTRAL_CARD_POOL: "none",
}


@dataclass(frozen=True, slots=True)
class ManaBadgeOcrResult:
    mana_cost: str
    mana_total: int
    text: str
    confidence: float
    lines: list[dict[str, Any]]
    scale: int
    bounds: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class ManaBadgeOcrAttempt:
    result: ManaBadgeOcrResult | None
    attempted_texts: list[str]
    bounds: tuple[int, int, int, int] | None


@dataclass(frozen=True, slots=True)
class TrailingOcrIntegerCandidate:
    token: str
    value: int


class NameManaCostParser:
    _EXPECTED_SYMBOL_TYPES = {"mana"}
    _DEFAULT_MANA_BADGE_OCR_SCALES = (3, 2)
    _trailing_integer_pattern = re.compile(r"(\d+)\s*$")
    _trailing_variable_x_pattern = re.compile(
        r"(?<![a-zA-Z0-9])x\s*$",
        re.IGNORECASE,
    )
    _leading_noise_number_pattern = re.compile(r"^\s*\d+(?:\s+\d+)?\s+")
    _integer_pattern = re.compile(r"\d+")
    _variable_x_pattern = re.compile(r"(?<![a-zA-Z0-9])x(?![a-zA-Z0-9])", re.IGNORECASE)

    def __init__(self, ocr_runner: OcrRunner, symbol_detector: SymbolDetector) -> None:
        self._ocr_runner = ocr_runner
        self._symbol_detector = symbol_detector

    def parse(
        self,
        *,
        region_name: str,
        image: Image.Image,
        image_stem: str,
        card_pool: CardPool,
        region_spec: dict[str, Any],
        symbols: list[Symbol],
    ) -> RegionParseResult:
        mana_source = self._mana_source(card_pool)
        logger.info(
            "Name/mana parser started. region=%s card_pool=%s mana_source=%s image_size=%sx%s",
            region_name,
            card_pool,
            mana_source,
            image.width,
            image.height,
        )
        ocr_text = read_name_ocr_text(
            ocr_runner=self._ocr_runner,
            image=image,
            region_spec=region_spec,
        )
        filtered_lines = ocr_text.lines
        full_text = ocr_text.text

        candidate_symbols: list[Symbol] = []
        detected_symbols: list[DetectedSymbol] = []
        mana_symbol_keys: list[str] = []
        mana_cost = ""
        mana_total = ""
        has_mana = False
        has_variable_x = False
        mana_badge_result: ManaBadgeOcrResult | None = None
        mana_badge_attempted_texts: list[str] = []
        mana_badge_bounds: tuple[int, int, int, int] | None = None
        trailing_integer_candidate: TrailingOcrIntegerCandidate | None = None
        trailing_integer_confirmed = False

        if mana_source == "symbols":
            candidate_symbols = self._select_mana_candidate_symbols(symbols)
            detected_symbols = self._symbol_detector.detect(
                image=image,
                symbols=candidate_symbols,
                expected_symbol_types=self._EXPECTED_SYMBOL_TYPES,
            )
            mana_symbol_keys = self._mana_symbol_keys(detected_symbols)
            variable_x_in_symbols = any(
                self._is_variable_symbol_key(key) for key in mana_symbol_keys
            )
            variable_x_in_ocr = self._has_variable_x_in_text(full_text)
            has_variable_x = variable_x_in_symbols or variable_x_in_ocr
            parsed_total = sum(
                self._mana_value_from_symbol_key(key) for key in mana_symbol_keys
            )
            if has_variable_x and not variable_x_in_symbols:
                mana_symbol_keys.append("x")
            mana_cost = self._format_mana_cost(
                mana_total=parsed_total,
                has_variable_x=has_variable_x,
            )
            mana_total = str(parsed_total)
            has_mana = parsed_total > 0 or bool(mana_symbol_keys) or has_variable_x
        elif mana_source == "trailing_ocr_integer":
            trailing_integer_candidate = self._extract_trailing_ocr_integer(full_text)
            mana_badge_attempt = self._read_evil_mana_badge(
                image=image,
                ocr_config=ocr_text.ocr_config,
                region_spec=region_spec,
            )
            mana_badge_result = mana_badge_attempt.result
            mana_badge_attempted_texts = mana_badge_attempt.attempted_texts
            mana_badge_bounds = mana_badge_attempt.bounds
            if mana_badge_result is not None:
                mana_cost = mana_badge_result.mana_cost
                mana_total = str(mana_badge_result.mana_total)
                has_mana = True
                has_variable_x = mana_cost == "X"
                trailing_integer_confirmed = bool(
                    trailing_integer_candidate is not None
                    and not has_variable_x
                    and mana_badge_result.mana_total
                    == trailing_integer_candidate.value
                )
                if has_variable_x:
                    mana_symbol_keys.append("x")
            elif (
                trailing_integer_candidate is not None
                and mana_badge_bounds is not None
                and self._primary_ocr_contains_badge_token(
                    filtered_lines,
                    token=trailing_integer_candidate.token,
                    bounds=mana_badge_bounds,
                )
            ):
                mana_cost = str(trailing_integer_candidate.value)
                mana_total = str(trailing_integer_candidate.value)
                has_mana = True
                trailing_integer_confirmed = True

        primary_ocr_contains_confirmed_badge_x = bool(
            mana_badge_result is not None
            and mana_badge_result.mana_cost == "X"
            and self._primary_ocr_contains_badge_token(
                filtered_lines,
                token="X",
                bounds=mana_badge_result.bounds,
            )
        )
        strip_trailing_integer = (
            has_mana if mana_source == "symbols" else trailing_integer_confirmed
        )
        name = (
            self._extract_name(
                full_text,
                has_mana=has_mana,
                strip_trailing_integer=strip_trailing_integer,
                confirmed_variable_x=primary_ocr_contains_confirmed_badge_x,
            )
            or image_stem
        )
        result_text = full_text
        result_lines = filtered_lines
        result_confidence = ocr_text.confidence
        if mana_badge_result is not None:
            result_text = "\n".join(
                part for part in (full_text, mana_badge_result.text) if part
            )
            result_lines = [*filtered_lines, *mana_badge_result.lines]

        field_confidences = {"name": ocr_text.confidence}
        if has_mana:
            field_confidences["mana_cost"] = (
                mana_badge_result.confidence
                if mana_badge_result is not None
                else ocr_text.confidence
            )

        logger.info(
            "Name/mana parse summary. text=%r card_pool=%s mana_source=%s symbols=%s symbol_keys=%s name=%r mana_cost=%r mana_total=%r",
            full_text,
            card_pool,
            mana_source,
            len(detected_symbols),
            mana_symbol_keys,
            name,
            mana_cost,
            mana_total,
        )
        if detected_symbols:
            logger.info(
                "Name/mana parse symbol_details=%s",
                [
                    {
                        "key": row.key,
                        "conf": row.confidence,
                        "x": row.bbox.x,
                        "y": row.bbox.y,
                        "w": row.bbox.w,
                        "h": row.bbox.h,
                    }
                    for row in detected_symbols[:12]
                ],
            )
        else:
            logger.info("Name/mana parse symbol_details=[]")
        logger.info(
            "Name/mana parser finished. region=%s conf=%.3f name=%r mana_cost=%r mana_symbols=%s",
            region_name,
            result_confidence,
            name,
            mana_cost,
            mana_symbol_keys,
        )

        normalized_fields: dict[str, str] = {
            "name": name,
            "mana_cost": mana_cost,
            "mana_symbols": " ".join(mana_symbol_keys).strip(),
            "mana_total": mana_total,
        }

        return RegionParseResult(
            region_name=region_name,
            text=result_text,
            confidence=result_confidence,
            lines=result_lines,
            detected_symbols=detected_symbols,
            normalized_fields=normalized_fields,
            field_confidences=field_confidences,
            debug={
                "card_pool": card_pool,
                "mana_source": mana_source,
                "expected_symbol_types": (
                    sorted(self._EXPECTED_SYMBOL_TYPES) if mana_source == "symbols" else []
                ),
                "full_ocr_text": full_text,
                "mana_badge_ocr": (
                    {
                        "text": mana_badge_result.text,
                        "confidence": mana_badge_result.confidence,
                        "scale": mana_badge_result.scale,
                        "line_count": len(mana_badge_result.lines),
                    }
                    if mana_badge_result is not None
                    else None
                ),
                "mana_badge_attempted_texts": mana_badge_attempted_texts,
                "mana_badge_bounds": mana_badge_bounds,
                "trailing_ocr_integer_candidate": (
                    {
                        "token": trailing_integer_candidate.token,
                        "value": trailing_integer_candidate.value,
                    }
                    if trailing_integer_candidate is not None
                    else None
                ),
                "trailing_ocr_integer_confirmed": trailing_integer_confirmed,
                "candidate_symbol_count": len(candidate_symbols),
                "ocr_config": ocr_text.ocr_config,
                "ocr_line_count_raw": ocr_text.raw_line_count,
                "ocr_line_count_filtered": len(filtered_lines),
            },
        )

    def _mana_source(self, card_pool: CardPool) -> ManaCostSource:
        try:
            return _MANA_COST_SOURCE_BY_POOL[card_pool]
        except KeyError as exc:
            raise ValueError(f"Unsupported card pool '{card_pool}'.") from exc

    def _select_mana_candidate_symbols(self, symbols: list[Symbol]) -> list[Symbol]:
        enabled_template = [row for row in symbols if row.enabled and row.detector_type == "template"]
        mana_typed = [row for row in enabled_template if row.symbol_type.strip().lower() == "mana"]
        logger.info(
            "Name/mana parser symbol candidates selected. total=%s mana=%s",
            len(enabled_template),
            len(mana_typed),
        )
        return mana_typed

    def _extract_name(
        self,
        text: str,
        *,
        has_mana: bool,
        strip_trailing_integer: bool,
        confirmed_variable_x: bool = False,
    ) -> str:
        compact = normalize_name_text(text)
        if not compact:
            return ""
        if has_mana:
            if strip_trailing_integer:
                compact = self._trailing_integer_pattern.sub("", compact).strip()
            if confirmed_variable_x:
                compact = self._trailing_variable_x_pattern.sub("", compact).strip()
            compact = self._leading_noise_number_pattern.sub("", compact).strip()
        return compact.strip()

    def _extract_trailing_ocr_integer(
        self,
        text: str,
    ) -> TrailingOcrIntegerCandidate | None:
        compact = " ".join(text.split())
        match = self._trailing_integer_pattern.search(compact)
        if match is None:
            return None
        try:
            return TrailingOcrIntegerCandidate(
                token=match.group(1),
                value=int(match.group(1)),
            )
        except ValueError:
            return None

    def _extract_standalone_ocr_mana(self, text: str) -> tuple[str, int] | None:
        compact = " ".join(text.split())
        integer_match = self._trailing_integer_pattern.fullmatch(compact)
        if integer_match is not None:
            try:
                value = int(integer_match.group(1))
            except ValueError:
                return None
            return str(value), value
        if self._trailing_variable_x_pattern.fullmatch(compact) is not None:
            return "X", 0
        return None

    def _read_evil_mana_badge(
        self,
        *,
        image: Image.Image,
        ocr_config: dict[str, object],
        region_spec: dict[str, Any],
    ) -> ManaBadgeOcrAttempt:
        badge_config = self._resolve_mana_badge_ocr_config(region_spec)
        if badge_config is None:
            return ManaBadgeOcrAttempt(result=None, attempted_texts=[], bounds=None)
        badge, left, top, scales = self._crop_mana_badge(
            image=image,
            config=badge_config,
        )
        badge_bounds = (left, top, left + badge.width, top + badge.height)
        attempted_texts: list[str] = []
        for scale in scales:
            scaled_badge = badge.resize(
                (badge.width * scale, badge.height * scale),
                Image.Resampling.LANCZOS,
            )
            ocr_data = self._ocr_runner.run(scaled_badge, config=ocr_config)
            badge_text = str(ocr_data.get("text", "")).strip()
            attempted_texts.append(badge_text)
            parsed_mana = self._extract_standalone_ocr_mana(badge_text)
            if parsed_mana is None:
                continue
            mana_cost, mana_total = parsed_mana
            return ManaBadgeOcrAttempt(
                result=ManaBadgeOcrResult(
                    mana_cost=mana_cost,
                    mana_total=mana_total,
                    text=badge_text,
                    confidence=self._safe_confidence(ocr_data.get("confidence", 0.0)),
                    lines=self._normalize_badge_lines(
                        self._safe_lines(ocr_data.get("lines", [])),
                        left=left,
                        top=top,
                        scale=scale,
                    ),
                    scale=scale,
                    bounds=badge_bounds,
                ),
                attempted_texts=attempted_texts,
                bounds=badge_bounds,
            )
        return ManaBadgeOcrAttempt(
            result=None,
            attempted_texts=attempted_texts,
            bounds=badge_bounds,
        )

    def _resolve_mana_badge_ocr_config(
        self,
        region_spec: dict[str, Any],
    ) -> dict[str, Any] | None:
        raw = region_spec.get("mana_badge_ocr")
        if not isinstance(raw, dict) or not isinstance(raw.get("cut_region"), dict):
            return None
        return raw

    def _crop_mana_badge(
        self,
        *,
        image: Image.Image,
        config: dict[str, Any],
    ) -> tuple[Image.Image, int, int, tuple[int, ...]]:
        bounds = config["cut_region"]
        unit = str(bounds.get("unit", "relative")).strip().lower()
        if unit == "relative":
            left = round(float(bounds.get("x", 0.0)) * image.width)
            top = round(float(bounds.get("y", 0.0)) * image.height)
            width = round(float(bounds.get("w", 1.0)) * image.width)
            height = round(float(bounds.get("h", 1.0)) * image.height)
        elif unit == "absolute":
            left = round(float(bounds.get("x", 0.0)))
            top = round(float(bounds.get("y", 0.0)))
            width = round(float(bounds.get("w", image.width)))
            height = round(float(bounds.get("h", image.height)))
        else:
            raise ValueError(f"Unsupported mana badge region unit '{unit}'.")

        left = max(0, min(left, image.width - 1))
        top = max(0, min(top, image.height - 1))
        width = max(1, min(width, image.width - left))
        height = max(1, min(height, image.height - top))
        scales = self._resolve_mana_badge_scales(config.get("scales"))
        return image.crop((left, top, left + width, top + height)), left, top, scales

    def _resolve_mana_badge_scales(self, raw: Any) -> tuple[int, ...]:
        if not isinstance(raw, list):
            return self._DEFAULT_MANA_BADGE_OCR_SCALES
        scales: list[int] = []
        for value in raw:
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or not 0 < value <= MAX_MANA_BADGE_OCR_SCALE
                or value in scales
            ):
                continue
            scales.append(value)
            if len(scales) == MAX_MANA_BADGE_OCR_ATTEMPTS:
                break
        return tuple(scales) or self._DEFAULT_MANA_BADGE_OCR_SCALES

    def _primary_ocr_contains_badge_token(
        self,
        lines: list[dict[str, Any]],
        *,
        token: str,
        bounds: tuple[int, int, int, int],
    ) -> bool:
        left, top, right, bottom = bounds
        for line in lines:
            # A combined row has no character-level boxes, so its trailing X may
            # belong to the title. Only a standalone row is safe to remove.
            if str(line.get("text", "")).strip().upper() != token.upper():
                continue
            x = line.get("x")
            y = line.get("y")
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                if left <= float(x) <= right and top <= float(y) <= bottom:
                    return True
        return False

    def _normalize_badge_lines(
        self,
        lines: list[dict[str, Any]],
        *,
        left: int,
        top: int,
        scale: int,
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for line in lines:
            row = dict(line)
            row["ocr_source"] = "mana_badge"
            if isinstance(row.get("x"), (int, float)):
                row["x"] = left + float(row["x"]) / scale
            if isinstance(row.get("y"), (int, float)):
                row["y"] = top + float(row["y"]) / scale
            box = row.get("box")
            if isinstance(box, list):
                row["box"] = [
                    (left + float(point[0]) / scale, top + float(point[1]) / scale)
                    for point in box
                    if isinstance(point, (list, tuple)) and len(point) >= 2
                ]
            normalized.append(row)
        return normalized

    def _safe_confidence(self, raw: Any) -> float:
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    def _safe_lines(self, raw: Any) -> list[dict[str, Any]]:
        return raw if isinstance(raw, list) else []

    def _mana_symbol_keys(self, rows: list[DetectedSymbol]) -> list[str]:
        ordered = sorted(rows, key=lambda row: row.bbox.x)
        out: list[str] = []
        for row in ordered:
            out.append(row.key)
        return out

    def _extract_integer_values_from_symbol_key(self, key: str) -> list[int]:
        out: list[int] = []
        for raw in self._integer_pattern.findall(key):
            try:
                out.append(int(raw))
            except ValueError:
                continue
        return out

    def _mana_value_from_symbol_key(self, key: str) -> int:
        if self._is_variable_symbol_key(key):
            return 0
        integer_values = self._extract_integer_values_from_symbol_key(key)
        if integer_values:
            return sum(integer_values)
        return 1

    def _has_variable_x_in_text(self, text: str) -> bool:
        return self._variable_x_pattern.search(text or "") is not None

    def _is_variable_symbol_key(self, key: str) -> bool:
        compact = (key or "").strip().lower().replace("_", "-")
        if compact == "x":
            return True
        return any(part == "x" for part in compact.split("-"))

    def _format_mana_cost(self, *, mana_total: int, has_variable_x: bool) -> str:
        if not has_variable_x:
            return str(mana_total)
        if mana_total <= 0:
            return "X"
        return f"X+{mana_total}"
