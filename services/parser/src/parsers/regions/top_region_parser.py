from __future__ import annotations

import logging
import re
from typing import Any

from models import Symbol
from PIL import Image

from parsers.ocr_runner import OcrRunner
from parsers.symbol_detector import SymbolDetector

from .types import RegionParseResult

logger = logging.getLogger(__name__)


class TopRegionParser:
    _EXPECTED_SYMBOL_TYPES = {"mana"}
    _star_tail_pattern = re.compile(r"\s*[★☆✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼✽✾✿]+.*$")
    _trailing_integer_pattern = re.compile(r"(\d+)\s*$")
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
        region_spec: dict[str, Any],
        symbols: list[Symbol],
    ) -> RegionParseResult:
        _ = region_spec
        width, _ = image.size
        ocr_data = self._ocr_runner.run(image)
        full_text = str(ocr_data.get("text", ""))
        candidate_symbols = self._select_mana_candidate_symbols(symbols)
        detected_symbols_all = self._symbol_detector.detect(
            image=image,
            symbols=candidate_symbols,
            expected_symbol_types=self._EXPECTED_SYMBOL_TYPES,
        )
        detected_symbols = detected_symbols_all
        mana_symbol_keys = self._mana_symbol_keys(detected_symbols)
        key_integer_values = self._extract_integer_values_from_symbol_keys(mana_symbol_keys)
        ocr_integer_values = self._extract_integer_values_from_text(full_text)
        integer_values = self._dedupe_preserving_order(key_integer_values + ocr_integer_values)
        variable_x_in_symbols = any(self._is_variable_symbol_key(key) for key in mana_symbol_keys)
        variable_x_in_ocr = self._has_variable_x_in_text(full_text)
        has_variable_x = variable_x_in_symbols or variable_x_in_ocr

        non_integer_symbol_count = sum(
            1
            for key in mana_symbol_keys
            if self._extract_integer_values_from_symbol_key(key) == [] and not self._is_variable_symbol_key(key)
        )
        if has_variable_x and not variable_x_in_symbols:
            mana_symbol_keys.append("x")

        mana_total = sum(integer_values) + non_integer_symbol_count
        mana_cost = self._format_mana_cost(mana_total=mana_total, has_variable_x=has_variable_x)
        any_color = sum(integer_values)
        name = self._extract_name(
            full_text,
            has_mana=any_color > 0 or len(mana_symbol_keys) > 0 or has_variable_x,
        ) or image_stem

        logger.info(
            "Top parse summary. text=%r any_color=%s symbols_all=%s symbols_right=%s symbol_keys=%s name=%r mana_cost=%r mana_total=%s",
            full_text,
            any_color,
            len(detected_symbols_all),
            len(detected_symbols),
            mana_symbol_keys,
            name,
            mana_cost,
            mana_total,
        )
        if detected_symbols_all:
            logger.info(
                "Top parse symbols_all_details=%s",
                [
                    {
                        "key": row.key,
                        "conf": row.confidence,
                        "x": row.bbox.x,
                        "y": row.bbox.y,
                        "w": row.bbox.w,
                        "h": row.bbox.h,
                    }
                    for row in detected_symbols_all[:12]
                ],
            )
        else:
            logger.info("Top parse symbols_all_details=[]")

        normalized_fields: dict[str, str] = {
            "name": name,
            "mana_cost": mana_cost,
            "mana_symbols": " ".join(mana_symbol_keys).strip(),
            "mana_total": str(mana_total),
        }

        return RegionParseResult(
            region_name=region_name,
            text=full_text,
            confidence=self._safe_confidence(ocr_data.get("confidence", 0.0)),
            lines=self._safe_lines(ocr_data.get("lines", [])),
            detected_symbols=detected_symbols,
            normalized_fields=normalized_fields,
            debug={
                "expected_symbol_types": sorted(self._EXPECTED_SYMBOL_TYPES),
                "full_ocr_text": full_text,
                "candidate_symbol_count": len(candidate_symbols),
            },
        )

    def _select_mana_candidate_symbols(self, symbols: list[Symbol]) -> list[Symbol]:
        enabled_template = [row for row in symbols if row.enabled and row.detector_type == "template"]
        mana_typed = [row for row in enabled_template if row.symbol_type.strip().lower() == "mana"]
        if mana_typed:
            logger.info(
                "Top parse symbol candidates: using mana-typed symbols. total=%s mana=%s",
                len(enabled_template),
                len(mana_typed),
            )
            return mana_typed

        logger.warning(
            "Top parse symbol candidates: no mana-typed symbols found; falling back to all template symbols. total=%s",
            len(enabled_template),
        )
        return enabled_template

    def _extract_name(self, text: str, *, has_mana: bool) -> str:
        compact = text.replace("\n", " ").strip()
        if not compact:
            return ""
        compact = self._star_tail_pattern.sub("", compact)
        if has_mana:
            compact = self._trailing_integer_pattern.sub("", compact).strip()
            compact = self._leading_noise_number_pattern.sub("", compact).strip()
        return compact.strip()

    def _mana_symbol_keys(self, rows: list[Any]) -> list[str]:
        ordered = sorted(rows, key=lambda row: row.bbox.x)
        out: list[str] = []
        for row in ordered:
            out.append(row.key)
        return out

    def _extract_any_color_mana(self, text: str) -> int:
        compact = text.replace("\n", " ").strip()
        match = self._trailing_integer_pattern.search(compact)
        if not match:
            return 0
        try:
            return int(match.group(1))
        except ValueError:
            return 0

    def _extract_integer_values_from_text(self, text: str) -> list[int]:
        out: list[int] = []
        for raw in self._integer_pattern.findall(text):
            try:
                out.append(int(raw))
            except ValueError:
                continue
        return out

    def _extract_integer_values_from_symbol_key(self, key: str) -> list[int]:
        out: list[int] = []
        for raw in self._integer_pattern.findall(key):
            try:
                out.append(int(raw))
            except ValueError:
                continue
        return out

    def _extract_integer_values_from_symbol_keys(self, keys: list[str]) -> list[int]:
        out: list[int] = []
        for key in keys:
            out.extend(self._extract_integer_values_from_symbol_key(key))
        return out

    def _has_variable_x_in_text(self, text: str) -> bool:
        return self._variable_x_pattern.search(text or "") is not None

    def _is_variable_symbol_key(self, key: str) -> bool:
        compact = (key or "").strip().lower().replace("_", "-")
        if compact == "x":
            return True
        return any(part == "x" for part in compact.split("-"))

    def _dedupe_preserving_order(self, values: list[int]) -> list[int]:
        out: list[int] = []
        seen: set[int] = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            out.append(value)
        return out

    def _format_mana_cost(self, *, mana_total: int, has_variable_x: bool) -> str:
        if not has_variable_x:
            return str(mana_total)
        if mana_total <= 0:
            return "X"
        return f"X+{mana_total}"

    def _build_mana_layout_text(self, any_color: int, symbol_keys: list[str]) -> str:
        tokens: list[str] = []
        if any_color > 0:
            tokens.append(str(any_color))
        tokens.extend([f"{{{key}}}" for key in symbol_keys])
        return " ".join(tokens).strip()

    def _safe_confidence(self, raw: Any) -> float:
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    def _safe_lines(self, raw: Any) -> list[dict[str, Any]]:
        return raw if isinstance(raw, list) else []
