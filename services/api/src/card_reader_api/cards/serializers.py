from __future__ import annotations
from typing import TYPE_CHECKING, TypedDict

from rest_framework import serializers

from card_reader_core.models import Card, CardVersion, Keyword, Symbol, Tag, Type
from card_reader_core.rule_text import render_enriched_rule_text

if TYPE_CHECKING:
    from card_reader_core.services.cards import CardEditState, CardMetadata

MetadataOption = Keyword | Tag | Type
SCALAR_FIELDS = {"name", "type_line", "mana_cost", "attack", "health", "rules_text"}
METADATA_GROUPS = {"keywords", "tags", "types", "symbols"}


class CardFilterParams(TypedDict):
    query: str | None
    max_confidence: float | None
    keyword_ids: list[str] | None
    tag_ids: list[str] | None
    symbol_ids: list[str] | None
    type_ids: list[str] | None
    mana_cost: str | None
    template_id: str | None
    attack_min: int | None
    attack_max: int | None
    health_min: int | None
    health_max: int | None


class CardListFilterParams(CardFilterParams):
    page: int
    page_size: int


def card_payload(
    card: Card,
    version: CardVersion,
    *,
    image_url: str | None,
    metadata: CardMetadata | None = None,
    edit_state: CardEditState | None = None,
) -> dict[str, object]:
    rendered_rule_text = _render_card_rule_text(version, metadata)
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
        "rules_text_enriched": version.rules_text_enriched or version.rules_text,
        "rules_text": rendered_rule_text,
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


def _render_card_rule_text(version: CardVersion, metadata: CardMetadata | None) -> str:
    if not version.rules_text_enriched:
        return version.rules_text
    if metadata is None:
        return version.rules_text
    symbol_tokens_by_key = {
        symbol.key: symbol.text_token
        for symbol in metadata["symbols"]
    }
    return render_enriched_rule_text(
        version.rules_text_enriched,
        symbol_tokens_by_key=symbol_tokens_by_key,
    )


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

    def validated_filters(self) -> CardFilterParams:
        return {
            "query": self._string_or_none("query"),
            "max_confidence": self._float_or_none("max_confidence"),
            "keyword_ids": self._string_list_or_none("keyword_ids"),
            "tag_ids": self._string_list_or_none("tag_ids"),
            "symbol_ids": self._string_list_or_none("symbol_ids"),
            "type_ids": self._string_list_or_none("type_ids"),
            "mana_cost": self._string_or_none("mana_cost"),
            "template_id": self._string_or_none("template_id"),
            "attack_min": self._int_or_none("attack_min"),
            "attack_max": self._int_or_none("attack_max"),
            "health_min": self._int_or_none("health_min"),
            "health_max": self._int_or_none("health_max"),
        }

    def validated_list_filters(self) -> CardListFilterParams:
        filters = self.validated_filters()
        return {
            **filters,
            "page": self._required_int("page"),
            "page_size": self._required_int("page_size"),
        }

    def _string_or_none(self, key: str) -> str | None:
        value = self.validated_data.get(key)
        return value if isinstance(value, str) else None

    def _float_or_none(self, key: str) -> float | None:
        value = self.validated_data.get(key)
        return value if isinstance(value, float) else None

    def _int_or_none(self, key: str) -> int | None:
        value = self.validated_data.get(key)
        return value if isinstance(value, int) else None

    def _required_int(self, key: str) -> int:
        value = self.validated_data.get(key)
        return value if isinstance(value, int) else 0

    def _string_list_or_none(self, key: str) -> list[str] | None:
        value = self.validated_data.get(key)
        if not isinstance(value, list):
            return None
        out = [item for item in value if isinstance(item, str)]
        return out or None


class LatestVersionUpdateSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(required=False, allow_blank=False)
    type_line = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    mana_cost = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    attack = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    health = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    rules_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    rules_text_enriched = serializers.CharField(required=False, allow_blank=True, allow_null=True)
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
        if "rules_text_enriched" in self.validated_data:
            updates["rules_text"] = self.validated_data["rules_text_enriched"]
        for field_name in ("keyword_ids", "tag_ids", "type_ids", "symbol_ids"):
            if field_name in self.validated_data:
                updates[field_name] = self.validated_data[field_name]
        return updates


def _validated_names(values: list[str], allowed: set[str], message: str) -> list[str]:
    if not all(value in allowed for value in values):
        raise serializers.ValidationError(message)
    return values
