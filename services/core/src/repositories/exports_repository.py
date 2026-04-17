from __future__ import annotations

import csv
import io

from sqlmodel import Session

from repositories.cards_repository import list_cards


def export_cards_csv(session: Session, *, query: str | None) -> str:
    cards = list_cards(session, query=query, max_confidence=None)
    stream = io.StringIO()
    writer = csv.DictWriter(
        stream,
        fieldnames=[
            "card_id",
            "card_key",
            "card_label",
            "version_id",
            "version_number",
            "name",
            "type_line",
            "mana_cost",
            "attack",
            "health",
            "rules_text",
            "template_id",
            "confidence",
        ],
    )
    writer.writeheader()
    for card, version in cards:
        writer.writerow(
            {
                "card_id": card.id,
                "card_key": card.key,
                "card_label": card.label,
                "version_id": version.id,
                "version_number": version.version_number,
                "name": version.name,
                "type_line": version.type_line,
                "mana_cost": version.mana_cost,
                "attack": version.attack,
                "health": version.health,
                "rules_text": version.rules_text,
                "template_id": version.template_id,
                "confidence": version.confidence,
            }
        )
    return stream.getvalue()


