from __future__ import annotations

import json
from collections import deque
from typing import Any

from card_reader_core.models import Symbol

from .symbol_detector import DetectedSymbol, DetectionBBox


def expand_implied_detections(
    *,
    detected_symbols: list[DetectedSymbol],
    symbols: list[Symbol],
) -> list[DetectedSymbol]:
    if not detected_symbols or not symbols:
        return detected_symbols

    symbol_by_id = {symbol.id: symbol for symbol in symbols}
    symbol_by_key = {symbol.key.strip().lower(): symbol for symbol in symbols if symbol.key.strip()}
    expanded = list(detected_symbols)
    seen = {_detection_identity(row) for row in detected_symbols}
    queue = deque(detected_symbols)

    while queue:
        detected = queue.popleft()
        source_symbol = symbol_by_id.get(detected.symbol_id)
        if source_symbol is None:
            continue
        for implied_symbol in _iter_implied_symbols(source_symbol, symbol_by_key):
            implied_detection = DetectedSymbol(
                symbol_id=implied_symbol.id,
                key=implied_symbol.key,
                symbol_type=implied_symbol.symbol_type,
                confidence=detected.confidence,
                bbox=DetectionBBox(
                    x=detected.bbox.x,
                    y=detected.bbox.y,
                    w=detected.bbox.w,
                    h=detected.bbox.h,
                ),
                detector_type=detected.detector_type,
                match_metadata={
                    **detected.match_metadata,
                    "implied": True,
                    "implied_by_symbol_id": detected.symbol_id,
                    "implied_by_symbol_key": detected.key,
                },
            )
            identity = _detection_identity(implied_detection)
            if identity in seen:
                continue
            seen.add(identity)
            expanded.append(implied_detection)
            queue.append(implied_detection)

    return expanded


def _iter_implied_symbols(
    symbol: Symbol,
    symbol_by_key: dict[str, Symbol],
) -> list[Symbol]:
    config = _normalize_config(symbol.detection_config_json)
    raw_keys = config.get("implied_symbol_keys")
    if not isinstance(raw_keys, list):
        return []

    out: list[Symbol] = []
    seen: set[str] = set()
    for item in raw_keys:
        if not isinstance(item, str):
            continue
        normalized_key = item.strip().lower()
        if not normalized_key or normalized_key in seen:
            continue
        seen.add(normalized_key)
        implied_symbol = symbol_by_key.get(normalized_key)
        if implied_symbol is not None:
            out.append(implied_symbol)
    return out


def _normalize_config(raw: object) -> dict[str, Any]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return {}
    if not isinstance(raw, dict):
        return {}
    return {str(key): value for key, value in raw.items()}


def _detection_identity(row: DetectedSymbol) -> tuple[str, int, int, int, int]:
    return (
        row.symbol_id,
        row.bbox.x,
        row.bbox.y,
        row.bbox.w,
        row.bbox.h,
    )
