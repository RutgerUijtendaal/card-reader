from __future__ import annotations

import csv
import io

from card_reader_core.models import Symbol
from card_reader_core.rule_text import render_enriched_rule_text

from .cards_repository import list_cards
from .metadata_repository import (
    list_symbols,
)


def export_cards_csv(
    *,
    query: str | None,
    max_confidence: float | None = None,
    keyword_ids: list[str] | None = None,
    tag_ids: list[str] | None = None,
    mana_symbol_ids: list[str] | None = None,
    mana_symbol_match: str | None = None,
    affinity_symbol_ids: list[str] | None = None,
    affinity_symbol_match: str | None = None,
    devotion_symbol_ids: list[str] | None = None,
    devotion_symbol_match: str | None = None,
    other_symbol_ids: list[str] | None = None,
    other_symbol_match: str | None = None,
    symbol_ids: list[str] | None = None,
    type_ids: list[str] | None = None,
    mana_cost: str | None = None,
    template_id: str | None = None,
    attack_min: int | None = None,
    attack_max: int | None = None,
    health_min: int | None = None,
    health_max: int | None = None,
) -> str:
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
    page = 1
    page_size = 100
    total_count = 0

    while True:
        cards = list_cards(
            query=query,
            max_confidence=max_confidence,
            keyword_ids=keyword_ids,
            tag_ids=tag_ids,
            mana_symbol_ids=mana_symbol_ids,
            mana_symbol_match=mana_symbol_match,
            affinity_symbol_ids=affinity_symbol_ids,
            affinity_symbol_match=affinity_symbol_match,
            devotion_symbol_ids=devotion_symbol_ids,
            devotion_symbol_match=devotion_symbol_match,
            other_symbol_ids=other_symbol_ids,
            other_symbol_match=other_symbol_match,
            symbol_ids=symbol_ids,
            type_ids=type_ids,
            mana_cost=mana_cost,
            template_id=template_id,
            attack_min=attack_min,
            attack_max=attack_max,
            health_min=health_min,
            health_max=health_max,
            page=page,
            page_size=page_size,
        )
        total_count = cards.count
        for row in cards.results:
            mana_symbols = [str(item) for item in row.version.mana_symbols_json if isinstance(item, str)]
            writer.writerow(
                {
                    "card_key": _sanitize_csv_text(row.version.card.key),
                    "name": _sanitize_csv_text(row.version.name),
                    "mana_cost": _sanitize_csv_text(row.version.mana_cost),
                    "mana_symbols": _replace_symbol_keys(_join_labels(mana_symbols)),
                    "attack": row.version.attack,
                    "health": row.version.health,
                    "rules_text": _sanitize_csv_text(
                        _render_rules_text(
                            row.version.rules_text_enriched,
                            row.version.rules_text,
                            row.symbols,
                        )
                    ),
                    "types": _join_labels([item.label for item in row.types]),
                    "tags": _join_labels([item.label for item in row.tags]),
                    "symbols": _join_labels([item.text_token for item in row.symbols]),
                    "keywords": _join_labels([item.label for item in row.keywords]),
                    "confidence": row.version.confidence,
                }
            )

        if page * cards.page_size >= total_count:
            break
        page += 1
    return stream.getvalue()


def _sanitize_csv_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _join_labels(labels: list[str]) -> str:
    clean = [_sanitize_csv_text(label) for label in labels if label.strip()]
    return ";".join(clean)


def _replace_symbol_keys(text: str) -> str:
    for symbol in list_symbols():
        text = text.replace(symbol.key, symbol.text_token)
    return text


def _render_rules_text(enriched_text: str, fallback_text: str, symbols: list[Symbol]) -> str:
    if not enriched_text:
        return fallback_text
    symbol_tokens_by_key = {
        getattr(symbol, "key", ""): getattr(symbol, "text_token", "")
        for symbol in symbols
        if getattr(symbol, "key", "")
    }
    return render_enriched_rule_text(
        enriched_text,
        symbol_tokens_by_key=symbol_tokens_by_key,
    )
