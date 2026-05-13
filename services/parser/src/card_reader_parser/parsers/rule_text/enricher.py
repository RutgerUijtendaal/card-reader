from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from card_reader_core.models import Symbol
from card_reader_core.rule_text import build_symbol_placeholder, render_enriched_rule_text

from ..symbol_detector import DetectedSymbol


@dataclass(slots=True)
class RuleTextEnrichmentResult:
    raw_text: str
    cleaned_text: str
    enriched_text: str
    rendered_text: str
    debug: dict[str, Any]


class RuleTextEnricher:
    def enrich(
        self,
        *,
        raw_text: str,
        detected_symbols: list[DetectedSymbol],
        symbols: list[Symbol],
    ) -> RuleTextEnrichmentResult:
        cleaned_text = _normalize_ocr_text(raw_text)
        symbols_by_id = {symbol.id: symbol for symbol in symbols}
        symbol_tokens_by_key = {symbol.key: symbol.text_token for symbol in symbols}
        detections_by_symbol_id = _group_detections_by_symbol_id(detected_symbols)

        enriched_text = cleaned_text
        applied_aliases: list[dict[str, object]] = []
        applied_anchors: list[dict[str, object]] = []

        for symbol_id, symbol_detections in detections_by_symbol_id.items():
            symbol = symbols_by_id.get(symbol_id)
            if symbol is None:
                continue

            remaining_occurrences = len(symbol_detections)
            placeholder = build_symbol_placeholder(symbol.key)
            config = _parse_text_enrichment_config(symbol.text_enrichment_json)

            for alias in config["ocr_aliases"]:
                if remaining_occurrences <= 0:
                    break
                enriched_text, replacements = _replace_alias_occurrences(
                    enriched_text,
                    alias=alias,
                    placeholder=placeholder,
                    max_replacements=remaining_occurrences,
                )
                if replacements > 0:
                    remaining_occurrences -= replacements
                    applied_aliases.append(
                        {"symbol_key": symbol.key, "alias": alias, "count": replacements}
                    )

            for anchor in config["pattern_anchors"]:
                if remaining_occurrences <= 0:
                    break
                match_text = anchor.get("match", "")
                position = anchor.get("position", "before")
                before_text = anchor.get("before_text", "")
                after_text = anchor.get("after_text", "")
                if not match_text:
                    continue
                enriched_text, insertions = _insert_anchor_occurrences(
                    enriched_text,
                    match_text=match_text,
                    placeholder=placeholder,
                    position=position,
                    before_text=before_text,
                    after_text=after_text,
                    max_insertions=remaining_occurrences,
                )
                if insertions > 0:
                    remaining_occurrences -= insertions
                    applied_anchors.append(
                        {
                            "symbol_key": symbol.key,
                            "match": match_text,
                            "position": position,
                            "before_text": before_text,
                            "after_text": after_text,
                            "count": insertions,
                        }
                    )

        rendered_text = render_enriched_rule_text(
            enriched_text,
            symbol_tokens_by_key=symbol_tokens_by_key,
        )
        return RuleTextEnrichmentResult(
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            enriched_text=enriched_text,
            rendered_text=rendered_text,
            debug={
                "applied_aliases": applied_aliases,
                "applied_anchors": applied_anchors,
                "detected_symbol_count": len(detected_symbols),
            },
        )


def _normalize_ocr_text(raw_text: str) -> str:
    normalized_lines = []
    for line in raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        compact = re.sub(r"[ \t]+", " ", line).strip()
        if compact:
            normalized_lines.append(compact)
    return "\n".join(normalized_lines)


def _group_detections_by_symbol_id(
    detected_symbols: list[DetectedSymbol],
) -> dict[str, list[DetectedSymbol]]:
    grouped: dict[str, list[DetectedSymbol]] = {}
    for row in sorted(detected_symbols, key=lambda item: (item.bbox.y, item.bbox.x, -item.confidence)):
        grouped.setdefault(row.symbol_id, []).append(row)
    return grouped


def _parse_text_enrichment_config(raw: object) -> dict[str, list[Any]]:
    if not isinstance(raw, dict):
        return {"ocr_aliases": [], "pattern_anchors": []}

    aliases = [item.strip() for item in raw.get("ocr_aliases", []) if isinstance(item, str) and item.strip()]
    anchors: list[dict[str, str]] = []
    for item in raw.get("pattern_anchors", []):
        if not isinstance(item, dict):
            continue
        match_text = item.get("match")
        position = item.get("position")
        if not isinstance(match_text, str) or not match_text:
            continue
        if position not in {"before", "after"}:
            position = "before"
        before_text = item.get("before_text")
        after_text = item.get("after_text")
        anchors.append(
            {
                "match": match_text,
                "position": position,
                "before_text": before_text if isinstance(before_text, str) else "",
                "after_text": after_text if isinstance(after_text, str) else "",
            }
        )
    return {"ocr_aliases": aliases, "pattern_anchors": anchors}


def _replace_alias_occurrences(
    text: str,
    *,
    alias: str,
    placeholder: str,
    max_replacements: int,
) -> tuple[str, int]:
    replaced = 0
    next_text = text
    while replaced < max_replacements:
        match = re.search(re.escape(alias), next_text, flags=re.IGNORECASE)
        if match is None:
            break
        next_text = f"{next_text[:match.start()]}{placeholder}{next_text[match.end():]}"
        replaced += 1
    return next_text, replaced


def _insert_anchor_occurrences(
    text: str,
    *,
    match_text: str,
    placeholder: str,
    position: str,
    before_text: str,
    after_text: str,
    max_insertions: int,
) -> tuple[str, int]:
    inserted = 0
    next_text = text
    search_start = 0

    while inserted < max_insertions:
        match_index = next_text.find(match_text, search_start)
        if match_index < 0:
            break

        if position == "before":
            insertion_text = _normalize_insertion_boundaries(
                text=next_text,
                insertion_index=match_index,
                insertion_text=f"{before_text}{placeholder}{after_text}",
            )
            insertion_index = match_index
            existing_start = max(0, insertion_index - len(insertion_text))
            if next_text[existing_start:insertion_index] == insertion_text:
                search_start = match_index + len(match_text)
                continue
        else:
            insertion_text = _normalize_insertion_boundaries(
                text=next_text,
                insertion_index=match_index + len(match_text),
                insertion_text=f"{before_text}{placeholder}{after_text}",
            )
            insertion_index = match_index + len(match_text)
            if next_text[insertion_index : insertion_index + len(insertion_text)] == insertion_text:
                search_start = insertion_index + len(insertion_text)
                continue

        next_text = f"{next_text[:insertion_index]}{insertion_text}{next_text[insertion_index:]}"
        inserted += 1
        search_start = insertion_index + len(insertion_text) + len(match_text)

    return next_text, inserted


def _normalize_insertion_boundaries(
    *,
    text: str,
    insertion_index: int,
    insertion_text: str,
) -> str:
    normalized = insertion_text
    if normalized.startswith(" ") and insertion_index > 0 and text[insertion_index - 1].isspace():
        normalized = normalized.lstrip(" ")
    if normalized.endswith(" ") and insertion_index < len(text) and text[insertion_index].isspace():
        normalized = normalized.rstrip(" ")
    return normalized
