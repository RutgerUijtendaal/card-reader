from __future__ import annotations

import json

from card_reader_core.models import Card, CardVersion, Symbol
from ..schemas import (
    CardResponse,
    MetadataOptionResponse,
    SymbolFilterOptionResponse,
)


def to_card_response(
    card: Card,
    version: CardVersion,
    *,
    image_url: str | None = None,
) -> CardResponse:
    return CardResponse(
        id=card.id,
        key=card.key,
        label=card.label,
        name=version.name,
        template_id=version.template_id,
        version_id=version.id,
        version_number=version.version_number,
        previous_version_id=version.previous_version_id,
        is_latest=version.is_latest,
        type_line=version.type_line,
        mana_cost=version.mana_cost,
        mana_symbols=_decode_mana_symbols(version.mana_symbols_json),
        attack=version.attack,
        health=version.health,
        rules_text=version.rules_text,
        confidence=version.confidence,
        created_at=version.created_at.isoformat(),
        image_url=image_url,
    )


def to_metadata_option_response(meta: object) -> MetadataOptionResponse:
    return MetadataOptionResponse(
        id=str(getattr(meta, "id", "")),
        key=str(getattr(meta, "key", "")),
        label=str(getattr(meta, "label", "")),
    )


def to_symbol_filter_option_response(symbol: Symbol) -> SymbolFilterOptionResponse:
    return SymbolFilterOptionResponse(
        id=symbol.id,
        key=symbol.key,
        label=symbol.label,
        symbol_type=symbol.symbol_type,
        text_token=symbol.text_token,
        asset_url=_first_symbol_asset_url(symbol.reference_assets_json),
    )


def _decode_mana_symbols(value: str) -> list[str]:
    try:
        payload = json.loads(value)
    except Exception:
        return []
    if isinstance(payload, list):
        return [str(item) for item in payload]
    return []


def _first_symbol_asset_url(raw: str) -> str | None:
    try:
        payload = json.loads(raw)
    except Exception:
        return None
    if not isinstance(payload, list):
        return None
    for item in payload:
        if not isinstance(item, str):
            continue
        relative = item.strip().replace("\\", "/")
        if not relative:
            continue
        return f"/symbols/assets/{relative}"
    return None
