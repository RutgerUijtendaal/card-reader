from __future__ import annotations
from typing import TYPE_CHECKING

from rest_framework import serializers

from card_reader_core.models import Card, CardVersion, Keyword, Symbol, Tag, Type

if TYPE_CHECKING:
    from card_reader_core.services.cards import CardEditState, CardMetadata

MetadataOption = Keyword | Tag | Type
SCALAR_FIELDS = {"name", "type_line", "mana_cost", "attack", "health", "rules_text"}
METADATA_GROUPS = {"keywords", "tags", "types", "symbols"}


def card_payload(
    card: Card,
    version: CardVersion,
    *,
    image_url: str | None,
    metadata: CardMetadata | None = None,
    edit_state: CardEditState | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": card.id,
        "key": card.key,
        "label": card.label,
        "name": version.name,
        "template_id": version.template.key,
        "version_id": version.id,
        "version_number": version.version_number,
        "previous_version_id": version.previous_version.id if version.previous_version is not None else None,
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
        "editable": version.is_latest,
        "keyword_ids": [],
        "tag_ids": [],
        "symbol_ids": [],
        "type_ids": [],
        "field_sources": {},
        "parsed_snapshot": {},
        "parse_result": None,
        "keywords": [],
        "tags": [],
        "symbols": [],
        "types": [],
    }
    if metadata is not None:
        payload.update(metadata_payload(metadata))
    if edit_state is not None:
        payload.update(edit_state_payload(edit_state))
    return payload


def metadata_payload(metadata: CardMetadata) -> dict[str, object]:
    return {
        "keywords": [row.label for row in metadata["keywords"]],
        "keyword_ids": [row.id for row in metadata["keywords"]],
        "tags": [metadata_option(row) for row in metadata["tags"]],
        "tag_ids": [row.id for row in metadata["tags"]],
        "symbols": [symbol_option(row) for row in metadata["symbols"]],
        "symbol_ids": [row.id for row in metadata["symbols"]],
        "types": [metadata_option(row) for row in metadata["types"]],
        "type_ids": [row.id for row in metadata["types"]],
    }


def edit_state_payload(edit_state: CardEditState) -> dict[str, object]:
    parse_result = edit_state["parse_result"]
    return {
        "field_sources": edit_state["field_sources"],
        "parsed_snapshot": edit_state["parsed_snapshot"],
        "parse_result": None
        if parse_result is None
        else {
            "id": parse_result.id,
            "created_at": parse_result.created_at.isoformat(),
        },
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


def _decode_mana_symbols(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _first_symbol_asset_url(raw: object) -> str | None:
    if not isinstance(raw, list):
        return None
    for item in raw:
        if isinstance(item, str) and item.strip():
            return f"/symbols/assets/{item.strip().replace('\\', '/')}"
    return None


class CardFiltersQuerySerializer(serializers.Serializer[dict[str, object]]):
    query = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    max_confidence = serializers.FloatField(required=False, allow_null=True)
    keyword_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    tag_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    symbol_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    type_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    mana_cost = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    template_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    attack_min = serializers.IntegerField(required=False, allow_null=True)
    attack_max = serializers.IntegerField(required=False, allow_null=True)
    health_min = serializers.IntegerField(required=False, allow_null=True)
    health_max = serializers.IntegerField(required=False, allow_null=True)
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, default=72)

    def validated_filters(self) -> dict[str, object]:
        data = dict(self.validated_data)
        for key in ("keyword_ids", "tag_ids", "symbol_ids", "type_ids"):
            if not data.get(key):
                data[key] = None
        return data


class LatestVersionUpdateSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(required=False, allow_blank=False)
    type_line = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    mana_cost = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    attack = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    health = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    rules_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    keyword_ids = serializers.ListField(child=serializers.CharField(), required=False)
    tag_ids = serializers.ListField(child=serializers.CharField(), required=False)
    type_ids = serializers.ListField(child=serializers.CharField(), required=False)
    symbol_ids = serializers.ListField(child=serializers.CharField(), required=False)
    restore_fields = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    restore_metadata_groups = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    unlock_fields = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    unlock_metadata_groups = serializers.ListField(child=serializers.CharField(), required=False, default=list)

    def validate_restore_fields(self, value: list[str]) -> list[str]:
        return _validated_names(value, SCALAR_FIELDS, "Invalid scalar field name.")

    def validate_unlock_fields(self, value: list[str]) -> list[str]:
        return _validated_names(value, SCALAR_FIELDS, "Invalid scalar field name.")

    def validate_restore_metadata_groups(self, value: list[str]) -> list[str]:
        return _validated_names(value, METADATA_GROUPS, "Invalid metadata group name.")

    def validate_unlock_metadata_groups(self, value: list[str]) -> list[str]:
        return _validated_names(value, METADATA_GROUPS, "Invalid metadata group name.")

    def validated_update_payload(self) -> dict[str, object]:
        updates: dict[str, object] = {}
        for field_name in SCALAR_FIELDS:
            if field_name in self.validated_data:
                updates[field_name] = self.validated_data[field_name]
        for field_name in ("keyword_ids", "tag_ids", "type_ids", "symbol_ids"):
            if field_name in self.validated_data:
                updates[field_name] = self.validated_data[field_name]
        return updates


def _validated_names(values: list[str], allowed: set[str], message: str) -> list[str]:
    if not all(value in allowed for value in values):
        raise serializers.ValidationError(message)
    return values
