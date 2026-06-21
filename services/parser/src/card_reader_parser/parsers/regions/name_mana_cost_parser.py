from __future__ import annotations

import logging
import re
from typing import Any

from card_reader_core.models import Symbol
from PIL import Image

from ..ocr_runner import OcrRunner
from ..region_config import resolve_region_ocr_config
from ..symbol_detector import SymbolDetector

from .types import RegionParseResult

logger = logging.getLogger(__name__)


class NameManaCostParser:
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
        logger.info(
            "Name/mana parser started. region=%s image_size=%sx%s expected_symbol_types=%s",
            region_name,
            image.width,
            image.height,
            sorted(self._EXPECTED_SYMBOL_TYPES),
        )
        ocr_config = resolve_region_ocr_config(region_spec)
        ocr_data = self._ocr_runner.run(image, config=ocr_config)
        filtered_lines = self._safe_lines(ocr_data.get("lines", []))
        full_text = self._join_line_texts(filtered_lines)

        candidate_symbols = self._select_mana_candidate_symbols(symbols)
        detected_symbols_all = self._symbol_detector.detect(
            image=image,
            symbols=candidate_symbols,
            expected_symbol_types=self._EXPECTED_SYMBOL_TYPES,
        )
        detected_symbols = detected_symbols_all
        mana_symbol_keys = self._mana_symbol_keys(detected_symbols)
        variable_x_in_symbols = any(self._is_variable_symbol_key(key) for key in mana_symbol_keys)
        variable_x_in_ocr = self._has_variable_x_in_text(full_text)
        has_variable_x = variable_x_in_symbols or variable_x_in_ocr

        mana_total = sum(self._mana_value_from_symbol_key(key) for key in mana_symbol_keys)
        if has_variable_x and not variable_x_in_symbols:
            mana_symbol_keys.append("x")

        mana_cost = self._format_mana_cost(mana_total=mana_total, has_variable_x=has_variable_x)
        name = self._extract_name(
            full_text,
            has_mana=mana_total > 0 or len(mana_symbol_keys) > 0 or has_variable_x,
        ) or image_stem

        logger.info(
            "Name/mana parse summary. text=%r symbol_mana_total=%s symbols_all=%s symbols_right=%s symbol_keys=%s name=%r mana_cost=%r mana_total=%s",
            full_text,
            mana_total,
            len(detected_symbols_all),
            len(detected_symbols),
            mana_symbol_keys,
            name,
            mana_cost,
            mana_total,
        )
        if detected_symbols_all:
            logger.info(
                "Name/mana parse symbols_all_details=%s",
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
            logger.info("Name/mana parse symbols_all_details=[]")
        logger.info(
            "Name/mana parser finished. region=%s conf=%.3f name=%r mana_cost=%r mana_symbols=%s",
            region_name,
            self._average_line_confidence(filtered_lines),
            name,
            mana_cost,
            mana_symbol_keys,
        )

        normalized_fields: dict[str, str] = {
            "name": name,
            "mana_cost": mana_cost,
            "mana_symbols": " ".join(mana_symbol_keys).strip(),
            "mana_total": str(mana_total),
        }

        return RegionParseResult(
            region_name=region_name,
            text=full_text,
            confidence=self._average_line_confidence(filtered_lines),
            lines=filtered_lines,
            detected_symbols=detected_symbols,
            normalized_fields=normalized_fields,
            debug={
                "expected_symbol_types": sorted(self._EXPECTED_SYMBOL_TYPES),
                "full_ocr_text": full_text,
                "candidate_symbol_count": len(candidate_symbols),
                "ocr_config": ocr_config,
                "ocr_line_count_raw": len(self._safe_lines(ocr_data.get("lines", []))),
                "ocr_line_count_filtered": len(filtered_lines),
            },
        )

    def _select_mana_candidate_symbols(self, symbols: list[Symbol]) -> list[Symbol]:
        enabled_template = [row for row in symbols if row.enabled and row.detector_type == "template"]
        mana_typed = [row for row in enabled_template if row.symbol_type.strip().lower() == "mana"]
        if mana_typed:
            logger.info(
                "Name/mana parser symbol candidates: using mana-typed symbols. total=%s mana=%s",
                len(enabled_template),
                len(mana_typed),
            )
            return mana_typed

        logger.warning(
            "Name/mana parser symbol candidates: no mana-typed symbols found; falling back to all template symbols. total=%s",
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

    def _join_line_texts(self, lines: list[dict[str, Any]]) -> str:
        return "\n".join(str(row.get("text", "")).strip() for row in lines if row.get("text")).strip()

    def _average_line_confidence(self, lines: list[dict[str, Any]]) -> float:
        if not lines:
            return 0.0
        values = [self._safe_confidence(row.get("confidence", 0.0)) for row in lines]
        return float(sum(values) / len(values))



