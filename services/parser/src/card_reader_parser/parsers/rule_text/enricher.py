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
                    alias_debug = {
                        "symbol_key": symbol.key,
                        "count": replacements,
                    }
                    alias_debug.update(alias)
                    applied_aliases.append(alias_debug)

            for anchor in config["pattern_anchors"]:
                if remaining_occurrences <= 0:
                    break
                match_text = anchor.get("match", "")
                match_regex = anchor.get("match_regex", "")
                position = anchor.get("position", "before")
                before_text = anchor.get("before_text", "")
                after_text = anchor.get("after_text", "")
                if not match_text and not match_regex:
                    continue
                enriched_text, insertions = _insert_anchor_occurrences(
                    enriched_text,
                    match_text=match_text,
                    match_regex=match_regex,
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
                            "match_regex": match_regex,
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

    aliases: list[dict[str, object]] = []
    for item in raw.get("ocr_aliases", []):
        if isinstance(item, str) and item.strip():
            aliases.append({"match": item.strip()})
            continue
        if not isinstance(item, dict):
            continue

        match_text = item.get("match")
        match_regex = item.get("match_regex")
        normalized_match = match_text if isinstance(match_text, str) else ""
        normalized_match_regex = match_regex if isinstance(match_regex, str) else ""
        if bool(normalized_match) == bool(normalized_match_regex):
            continue

        replace_group = item.get("replace_group", 0)
        if not isinstance(replace_group, int) or replace_group < 0:
            replace_group = 0
        aliases.append(
            {
                "match": normalized_match,
                "match_regex": normalized_match_regex,
                "replace_group": replace_group,
            }
        )

    anchors: list[dict[str, str]] = []
    for item in raw.get("pattern_anchors", []):
        if not isinstance(item, dict):
            continue
        match_text = item.get("match")
        match_regex = item.get("match_regex")
        position = item.get("position")
        normalized_match = match_text if isinstance(match_text, str) else ""
        normalized_match_regex = match_regex if isinstance(match_regex, str) else ""
        if bool(normalized_match) == bool(normalized_match_regex):
            continue
        if position not in {"before", "after"}:
            position = "before"
        before_text = item.get("before_text")
        after_text = item.get("after_text")
        anchors.append(
            {
                "match": normalized_match,
                "match_regex": normalized_match_regex,
                "position": position,
                "before_text": before_text if isinstance(before_text, str) else "",
                "after_text": after_text if isinstance(after_text, str) else "",
            }
        )
    return {"ocr_aliases": aliases, "pattern_anchors": anchors}


def _replace_alias_occurrences(
    text: str,
    *,
    alias: dict[str, object],
    placeholder: str,
    max_replacements: int,
) -> tuple[str, int]:
    replaced = 0
    next_text = text
    match_text = alias.get("match", "")
    match_regex = alias.get("match_regex", "")
    replace_group = alias.get("replace_group", 0)
    if not isinstance(match_text, str):
        match_text = ""
    if not isinstance(match_regex, str):
        match_regex = ""
    if not isinstance(replace_group, int):
        replace_group = 0

    while replaced < max_replacements:
        match_bounds = _find_alias_match(
            next_text,
            match_text=match_text,
            match_regex=match_regex,
            replace_group=replace_group,
        )
        if match_bounds is None:
            break
        start, end = match_bounds
        next_text = f"{next_text[:start]}{placeholder}{next_text[end:]}"
        replaced += 1
    return next_text, replaced


def _find_alias_match(
    text: str,
    *,
    match_text: str,
    match_regex: str,
    replace_group: int,
) -> tuple[int, int] | None:
    if match_regex:
        match = re.search(match_regex, text, flags=re.IGNORECASE)
        if match is None:
            return None
        if replace_group > 0:
            try:
                start, end = match.span(replace_group)
            except IndexError:
                return None
            if start < 0 or end < 0:
                return None
            return start, end
        return match.start(), match.end()

    match = re.search(re.escape(match_text), text, flags=re.IGNORECASE)
    if match is None:
        return None
    return match.start(), match.end()


def _insert_anchor_occurrences(
    text: str,
    *,
    match_text: str,
    match_regex: str,
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
        match_bounds = _find_anchor_match(
            next_text,
            match_text=match_text,
            match_regex=match_regex,
            search_start=search_start,
        )
        if match_bounds is None:
            break
        match_index, match_end = match_bounds

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
                insertion_index=match_end,
                insertion_text=f"{before_text}{placeholder}{after_text}",
            )
            insertion_index = match_end
            if next_text[insertion_index : insertion_index + len(insertion_text)] == insertion_text:
                search_start = insertion_index + len(insertion_text)
                continue

        next_text = f"{next_text[:insertion_index]}{insertion_text}{next_text[insertion_index:]}"
        inserted += 1
        search_start = insertion_index + len(insertion_text)

    return next_text, inserted


def _find_anchor_match(
    text: str,
    *,
    match_text: str,
    match_regex: str,
    search_start: int,
) -> tuple[int, int] | None:
    if match_regex:
        match = re.search(match_regex, text[search_start:], flags=re.IGNORECASE)
        if match is None:
            return None
        start = search_start + match.start()
        end = search_start + match.end()
        return start, end

    match_index = text.find(match_text, search_start)
    if match_index < 0:
        return None
    return match_index, match_index + len(match_text)


def _normalize_insertion_boundaries(
    *,
    text: str,
    insertion_index: int,
    insertion_text: str,
) -> str:
    normalized = insertion_text
    if normalized.startswith(" ") and insertion_index > 0 and text[insertion_index - 1].isspace():
        normalized = normalized.lstrip(" ")
    if normalized.endswith(" "):
        if insertion_index >= len(text):
            normalized = normalized.rstrip(" ")
        elif text[insertion_index].isspace():
            normalized = normalized.rstrip(" ")
    return normalized
