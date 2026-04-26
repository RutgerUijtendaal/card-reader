from __future__ import annotations

import csv
import io
import json
from typing import Any

from .cards_repository import list_cards
from .metadata_repository import (
    get_keywords_for_card_version,
    get_symbols_for_card_version,
    get_tags_for_card_version,
    get_types_for_card_version,
    list_symbols,
)


def export_cards_csv(
    _session: Any,
    *,
    query: str | None,
    max_confidence: float | None = None,
    keyword_ids: list[str] | None = None,
    tag_ids: list[str] | None = None,
    symbol_ids: list[str] | None = None,
    type_ids: list[str] | None = None,
    mana_cost: str | None = None,
    template_id: str | None = None,
    attack_min: int | None = None,
    attack_max: int | None = None,
    health_min: int | None = None,
    health_max: int | None = None,
) -> str:
    cards = list_cards(
        None,
        query=query,
        max_confidence=max_confidence,
        keyword_ids=keyword_ids,
        tag_ids=tag_ids,
        symbol_ids=symbol_ids,
        type_ids=type_ids,
        mana_cost=mana_cost,
        template_id=template_id,
        attack_min=attack_min,
        attack_max=attack_max,
        health_min=health_min,
        health_max=health_max,
    )
    stream = io.StringIO()
    writer = csv.DictWriter(
        stream,
        fieldnames=[
            "card_key",
            "name",
            "mana_cost",
            "mana_symbols",
            "attack",
            "health",
            "rules_text",
            "types",
            "tags",
            "symbols",
            "keywords",
            "confidence",
        ],
    )
    writer.writeheader()
    for card, version in cards:
        type_labels = [item.label for item in get_types_for_card_version(None, version.id)]
        tag_labels = [item.label for item in get_tags_for_card_version(None, version.id)]
        symbol_text_tokens = [item.text_token for item in get_symbols_for_card_version(None, version.id)]
        keyword_labels = [item.label for item in get_keywords_for_card_version(None, version.id)]
        mana_symbols = json.loads(version.mana_symbols_json)

        writer.writerow(
            {
                "card_key": _sanitize_csv_text(card.key),
                "name": _sanitize_csv_text(version.name),
                "mana_cost": _sanitize_csv_text(version.mana_cost),
                "mana_symbols": _replace_symbol_keys(_join_labels(mana_symbols)),
                "attack": version.attack,
                "health": version.health,
                "rules_text": _sanitize_csv_text(version.rules_text),
                "types": _join_labels(type_labels),
                "tags": _join_labels(tag_labels),
                "symbols": _join_labels(symbol_text_tokens),
                "keywords": _join_labels(keyword_labels),
                "confidence": version.confidence,
            }
        )
    return stream.getvalue()


def _sanitize_csv_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _join_labels(labels: list[str]) -> str:
    clean = [_sanitize_csv_text(label) for label in labels if label.strip()]
    return ";".join(clean)


def _replace_symbol_keys(text: str) -> str:
    for symbol in list_symbols(None):
        text = text.replace(symbol.key, symbol.text_token)
    return text
