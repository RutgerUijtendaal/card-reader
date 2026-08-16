from __future__ import annotations

import logging
import re
from typing import Any, Literal

from card_reader_core.models import (
    EVIL_CARD_POOL,
    NEUTRAL_CARD_POOL,
    PLAYER_CARD_POOL,
    CardPool,
    Symbol,
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


class NameManaCostParser:
    _EXPECTED_SYMBOL_TYPES = {"mana"}
    _MANA_BADGE_LEFT_RATIO = 0.86
    _MANA_BADGE_OCR_SCALES = (3, 2)
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
        mana_badge_ocr_text = ""

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
            evil_mana = self._extract_trailing_ocr_mana(full_text)
            if evil_mana is None:
                evil_mana, mana_badge_ocr_text = self._read_evil_mana_badge(
                    image=image,
                    ocr_config=ocr_text.ocr_config,
                )
            if evil_mana is not None:
                mana_cost, parsed_total = evil_mana
                mana_total = str(parsed_total)
                has_mana = True
                has_variable_x = mana_cost == "X"
                if has_variable_x:
                    mana_symbol_keys.append("x")

        name = self._extract_name(
            full_text,
            has_mana=has_mana,
            has_variable_x=(
                has_variable_x and mana_source == "trailing_ocr_integer"
            ),
        ) or image_stem

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
            ocr_text.confidence,
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
            text=full_text,
            confidence=ocr_text.confidence,
            lines=filtered_lines,
            detected_symbols=detected_symbols,
            normalized_fields=normalized_fields,
            debug={
                "card_pool": card_pool,
                "mana_source": mana_source,
                "expected_symbol_types": (
                    sorted(self._EXPECTED_SYMBOL_TYPES) if mana_source == "symbols" else []
                ),
                "full_ocr_text": full_text,
                "mana_badge_ocr_text": mana_badge_ocr_text,
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
        has_variable_x: bool,
    ) -> str:
        compact = normalize_name_text(text)
        if not compact:
            return ""
        if has_mana:
            compact = self._trailing_integer_pattern.sub("", compact).strip()
            if has_variable_x:
                compact = self._trailing_variable_x_pattern.sub("", compact).strip()
            compact = self._leading_noise_number_pattern.sub("", compact).strip()
        return compact.strip()

    def _extract_trailing_ocr_mana(self, text: str) -> tuple[str, int] | None:
        compact = " ".join(text.split())
        match = self._trailing_integer_pattern.search(compact)
        if match is not None:
            try:
                value = int(match.group(1))
            except ValueError:
                return None
            return str(value), value
        if self._trailing_variable_x_pattern.search(compact) is not None:
            return "X", 0
        return None

    def _read_evil_mana_badge(
        self,
        *,
        image: Image.Image,
        ocr_config: dict[str, object],
    ) -> tuple[tuple[str, int] | None, str]:
        left = min(
            image.width - 1,
            max(0, round(image.width * self._MANA_BADGE_LEFT_RATIO)),
        )
        badge = image.crop((left, 0, image.width, image.height))
        attempted_texts: list[str] = []
        for scale in self._MANA_BADGE_OCR_SCALES:
            scaled_badge = badge.resize(
                (badge.width * scale, badge.height * scale),
                Image.Resampling.LANCZOS,
            )
            ocr_data = self._ocr_runner.run(scaled_badge, config=ocr_config)
            badge_text = str(ocr_data.get("text", "")).strip()
            attempted_texts.append(badge_text)
            compact = " ".join(badge_text.split())
            if self._trailing_integer_pattern.fullmatch(compact) is not None:
                return self._extract_trailing_ocr_mana(compact), badge_text
            if self._trailing_variable_x_pattern.fullmatch(compact) is not None:
                return self._extract_trailing_ocr_mana(compact), badge_text
        return None, " | ".join(attempted_texts)

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

