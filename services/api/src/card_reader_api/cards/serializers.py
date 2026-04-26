from __future__ import annotations

import json
from typing import TYPE_CHECKING

from card_reader_core.models import Card, CardVersion, Keyword, Symbol, Tag, Type

if TYPE_CHECKING:
    from card_reader_core.services.cards import CardMetadata

MetadataOption = Keyword | Tag | Type


def card_payload(
    card: Card,
    version: CardVersion,
    *,
    image_url: str | None,
    metadata: CardMetadata | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": card.id,
        "key": card.key,
        "label": card.label,
        "name": version.name,
        "template_id": version.template_id,
        "version_id": version.id,
        "version_number": version.version_number,
        "previous_version_id": version.previous_version_id,
        "is_latest": version.is_latest,
        "type_line": version.type_line,
        "mana_cost": version.mana_cost,
        "mana_symbols": _decode_mana_symbols(version.mana_symbols_json),
        "attack": version.attack,
        "health": version.health,
        "rules_text": version.rules_text,
        "confidence": version.confidence,
        "created_at": version.created_at.isoformat(),
        "image_url": image_url,
        "keywords": [],
        "tags": [],
        "symbols": [],
        "types": [],
    }
    if metadata is not None:
        payload.update(metadata_payload(metadata))
    return payload


def metadata_payload(metadata: CardMetadata) -> dict[str, object]:
    return {
        "keywords": [row.label for row in metadata["keywords"]],
        "tags": [metadata_option(row) for row in metadata["tags"]],
        "symbols": [symbol_option(row) for row in metadata["symbols"]],
        "types": [metadata_option(row) for row in metadata["types"]],
    }


def metadata_option(row: MetadataOption) -> dict[str, str]:
    return {"id": str(row.id), "key": str(row.key), "label": str(row.label)}


def symbol_option(symbol: Symbol) -> dict[str, object]:
    return {
        "id": symbol.id,
        "key": symbol.key,
        "label": symbol.label,
        "symbol_type": symbol.symbol_type,
        "text_token": symbol.text_token,
        "asset_url": _first_symbol_asset_url(symbol.reference_assets_json),
    }


def _decode_mana_symbols(value: str) -> list[str]:
    try:
        payload = json.loads(value)
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    return [str(item) for item in payload]


def _first_symbol_asset_url(raw: str) -> str | None:
    try:
        payload = json.loads(raw)
    except Exception:
        return None
    if not isinstance(payload, list):
        return None
    for item in payload:
        if isinstance(item, str) and item.strip():
            return f"/symbols/assets/{item.strip().replace('\\', '/')}"
    return None
