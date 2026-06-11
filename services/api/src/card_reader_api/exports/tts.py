from __future__ import annotations

import base64
import json
from typing import Any

from django.utils.text import slugify


def encode_tts_deck_export(deck: Any, *, sideboard_id: str | None = None) -> str:
    payload = _build_tts_export_payload(deck, sideboard_id=sideboard_id)
    json_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return base64.b64encode(json_bytes).decode("ascii")


def tts_export_filename(deck_name: str, *, sideboard_name: str | None = None) -> str:
    safe_name = slugify(_export_name(deck_name, sideboard_name=sideboard_name)) or "deck"
    return f"{safe_name}.tts.txt"


def get_tts_export_sideboard(deck: Any, sideboard_id: str | None) -> Any | None:
    if sideboard_id is None:
        return None
    return next((sideboard for sideboard in deck.sideboards.all() if str(sideboard.id) == sideboard_id), None)


def _build_tts_export_payload(deck: Any, *, sideboard_id: str | None) -> dict[str, object]:
    sideboard = get_tts_export_sideboard(deck, sideboard_id)
    if sideboard is not None:
        return _build_tts_sideboard_export_payload(deck, sideboard)

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


def _build_tts_sideboard_export_payload(deck: Any, sideboard: Any) -> dict[str, object]:
    entries = list(sideboard.entries.select_related("card__latest_version").all())
    return {
        "schema": "card-reader.tts-deck.v1",
        "deck": {
            "name": _export_name(deck.name, sideboard_name=sideboard.name),
            "description": deck.description,
        },
        "cards": [
            _build_tts_export_card_ref(entry.card, quantity=entry.quantity, role="sideboard")
            for entry in entries
        ],
    }


def _export_name(deck_name: str, *, sideboard_name: str | None) -> str:
    return deck_name if sideboard_name is None else f"{deck_name} - {sideboard_name}"


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
