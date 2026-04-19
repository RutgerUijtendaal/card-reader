from __future__ import annotations

import csv
import io

from sqlmodel import Session

from repositories.cards_repository import list_cards
from repositories.metadata_repository import (
    get_keywords_for_card_version,
    get_symbols_for_card_version,
    get_tags_for_card_version,
    get_types_for_card_version,
)


def export_cards_csv(
    session: Session,
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
        session,
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
        type_labels = [item.label for item in get_types_for_card_version(session, version.id)]
        tag_labels = [item.label for item in get_tags_for_card_version(session, version.id)]
        symbol_labels = [item.label for item in get_symbols_for_card_version(session, version.id)]
        keyword_labels = [item.label for item in get_keywords_for_card_version(session, version.id)]

        writer.writerow(
            {
                "card_key": _sanitize_csv_text(card.key),
                "name": _sanitize_csv_text(version.name),
                "mana_cost": _sanitize_csv_text(version.mana_cost),
                "attack": version.attack,
                "health": version.health,
                "rules_text": _sanitize_csv_text(version.rules_text),
                "types": _join_labels(type_labels),
                "tags": _join_labels(tag_labels),
                "symbols": _join_labels(symbol_labels),
                "keywords": _join_labels(keyword_labels),
                "confidence": version.confidence,
            }
        )
    return stream.getvalue()


def _sanitize_csv_text(value: str) -> str:
    return " ".join(value.split())


def _join_labels(labels: list[str]) -> str:
    clean = [_sanitize_csv_text(label) for label in labels if label.strip()]
    return ";".join(clean)


