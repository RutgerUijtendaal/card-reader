from __future__ import annotations

import base64
import json
from typing import Any

from django.utils.text import slugify


def encode_tts_deck_export(deck: Any) -> str:
    payload = _build_tts_export_payload(deck)
    json_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return base64.b64encode(json_bytes).decode("ascii")


def tts_export_filename(deck_name: str) -> str:
    safe_name = slugify(deck_name) or "deck"
    return f"{safe_name}.tts.txt"


def _build_tts_export_payload(deck: Any) -> dict[str, object]:
    entries = list(deck.entries.select_related("card__latest_version").all())
    hero_card = deck.hero_card

    return {
        "schema": "card-reader.tts-deck.v1",
        "deck": {
            "name": deck.name,
            "description": deck.description,
        },
        "hero": _build_tts_export_card_ref(hero_card, quantity=1, role="hero"),
        "cards": [
            _build_tts_export_card_ref(entry.card, quantity=entry.quantity, role="mainboard")
            for entry in entries
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
        "name": getattr(version, "name", None) or card.label,
    }
