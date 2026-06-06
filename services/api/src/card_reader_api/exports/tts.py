from __future__ import annotations

import base64
import json
from typing import Any

from django.utils.text import slugify

from card_reader_core.services.decks import DeckService


def encode_tts_deck_export(deck: Any) -> str:
    payload = _build_tts_export_payload(deck)
    json_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return base64.b64encode(json_bytes).decode("ascii")


def tts_export_filename(deck_name: str) -> str:
    safe_name = slugify(deck_name) or "deck"
    return f"{safe_name}.tts.txt"


def _build_tts_export_payload(deck: Any) -> dict[str, object]:
    entries = list(deck.entries.select_related("card__latest_version").all())
    sideboards = list(deck.sideboards.all())
    validation = DeckService().get_deck_validation(deck)
    totals = DeckService().get_deck_totals(deck)
    hero_card = deck.hero_card

    return {
        "schema": "card-reader.tts-deck.v1",
        "deck": {
            "id": deck.id,
            "name": deck.name,
            "description": deck.description,
            "total_cards": validation.total_cards,
            "unique_cards": validation.unique_cards,
            "overall_total_cards": totals.overall_total_cards,
            "overall_unique_cards": totals.overall_unique_cards,
            "mainboard_total_cards": totals.mainboard_total_cards,
            "mainboard_unique_cards": totals.mainboard_unique_cards,
        },
        "lookup": {
            "preferred_keys": ["card_id", "card_key", "name"],
        },
        "hero": _build_tts_export_card_ref(hero_card, quantity=1, role="hero"),
        "cards": [
            _build_tts_export_card_ref(entry.card, quantity=entry.quantity, role="mainboard")
            for entry in entries
        ],
        "sideboards": [
            {
                "name": sideboard.name,
                "cards": [
                    _build_tts_export_card_ref(
                        entry.card,
                        quantity=entry.quantity,
                        role="sideboard",
                    )
                    for entry in sideboard.entries.all()
                ],
            }
            for sideboard in sideboards
        ],
    }


def _build_tts_export_card_ref(
    card: Any,
    *,
    quantity: int,
    role: str,
) -> dict[str, object]:
    version = getattr(card, "latest_version", None)
    return {
        "role": role,
        "quantity": quantity,
        "card_id": card.id,
        "card_key": card.key,
        "name": getattr(version, "name", None) or card.label,
    }
