from __future__ import annotations

import json

from rest_framework import serializers

from card_reader_core.models import Card, CardVersion, Symbol


class MetadataOptionSerializer(serializers.Serializer):
    id = serializers.CharField()
    key = serializers.CharField()
    label = serializers.CharField()


class SymbolFilterOptionSerializer(MetadataOptionSerializer):
    symbol_type = serializers.CharField(default="generic")
    text_token = serializers.CharField(default="")
    asset_url = serializers.CharField(allow_null=True, required=False)


class CardSerializer(serializers.Serializer):
    id = serializers.CharField()
    key = serializers.CharField()
    label = serializers.CharField()
    name = serializers.CharField()
    template_id = serializers.CharField()
    version_id = serializers.CharField()
    version_number = serializers.IntegerField()
    previous_version_id = serializers.CharField(allow_null=True)
    is_latest = serializers.BooleanField()
    type_line = serializers.CharField()
    mana_cost = serializers.CharField()
    mana_symbols = serializers.ListField(child=serializers.CharField())
    attack = serializers.IntegerField(allow_null=True)
    health = serializers.IntegerField(allow_null=True)
    rules_text = serializers.CharField()
    confidence = serializers.FloatField()
    created_at = serializers.CharField()
    image_url = serializers.CharField(allow_null=True)
    keywords = serializers.ListField(child=serializers.CharField(), default=list)
    tags = MetadataOptionSerializer(many=True, default=list)
    symbols = SymbolFilterOptionSerializer(many=True, default=list)
    types = MetadataOptionSerializer(many=True, default=list)


def card_payload(
    card: Card,
    version: CardVersion,
    *,
    image_url: str | None,
    metadata: dict[str, list[object]] | None = None,
) -> dict[str, object]:
    payload = {
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
    return CardSerializer(payload).data


def metadata_payload(metadata: dict[str, list[object]]) -> dict[str, object]:
    return {
        "keywords": [row.label for row in metadata["keywords"]],
        "tags": [metadata_option(row) for row in metadata["tags"]],
        "symbols": [symbol_option(row) for row in metadata["symbols"]],
        "types": [metadata_option(row) for row in metadata["types"]],
    }


def metadata_option(row: object) -> dict[str, str]:
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
