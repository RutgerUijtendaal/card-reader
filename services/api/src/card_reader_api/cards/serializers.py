from __future__ import annotations
from typing import TYPE_CHECKING, TypedDict

from rest_framework import serializers

from card_reader_core.models import Card, CardVersion, Keyword, Symbol, Tag, Type
from card_reader_core.repositories.cards import DEFAULT_CARD_PAGE_SIZE
from card_reader_core.repositories.cards_repository import CARD_SORT_UPDATED_DESC, CARD_SORT_VALUES
from card_reader_core.rule_text import render_enriched_rule_text

if TYPE_CHECKING:
    from card_reader_core.models import CardGroup
    from card_reader_core.repositories.cards_repository import CardSort
    from card_reader_core.services.cards import CardEditState, CardMetadata

MetadataOption = Keyword | Tag | Type
SCALAR_FIELDS = {"name", "type_line", "mana_cost", "attack", "health", "rules_text"}
METADATA_GROUPS = {"keywords", "tags", "types", "symbols"}


class CardFilterParams(TypedDict):
    query: str | None
    card_ids: list[str] | None
    max_confidence: float | None
    keyword_ids: list[str] | None
    keyword_match: str | None
    tag_ids: list[str] | None
    tag_match: str | None
    mana_symbol_ids: list[str] | None
    mana_symbol_match: str | None
    affinity_symbol_ids: list[str] | None
    affinity_symbol_match: str | None
    devotion_symbol_ids: list[str] | None
    devotion_symbol_match: str | None
    other_symbol_ids: list[str] | None
    other_symbol_match: str | None
    symbol_ids: list[str] | None
    type_ids: list[str] | None
    type_match: str | None
    mana_cost_min: int | None
    mana_cost_max: int | None
    template_id: str | None
    is_hero: bool | None
    attack_min: int | None
    attack_max: int | None
    health_min: int | None
    health_max: int | None
    sort: CardSort


class CardListFilterParams(CardFilterParams):
    page: int
    page_size: int
    show_groups: bool


def card_payload(
    card: Card,
    version: CardVersion,
    *,
    image_url: str | None,
    metadata: CardMetadata | None = None,
    edit_state: CardEditState | None = None,
    card_groups: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    rendered_rule_text = _render_card_rule_text(version, metadata)
    payload: dict[str, object] = {
        "id": card.id,
        "result_type": "card",
        "key": card.key,
        "label": card.label,
        "name": version.name,
        "is_hero": card.is_hero,
        "template_id": version.template.key,
        "version_id": version.id,
        "version_number": version.version_number,
        "previous_version_id": version.previous_version.id if version.previous_version is not None else None,
        "is_latest": version.is_latest,
        "type_line": version.type_line,
        "mana_cost": version.mana_cost,
        "mana_symbols": _decode_mana_symbols(version.mana_symbols_json),
        "mana_value": version.mana_value,
        "attack": version.attack,
        "health": version.health,
        "rules_text_enriched": version.rules_text_enriched or version.rules_text,
        "rules_text": rendered_rule_text,
        "confidence": version.confidence,
        "created_at": version.created_at.isoformat(),
        "updated_at": version.updated_at.isoformat(),
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
        "card_groups": card_groups or [],
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


def metadata_option(row: MetadataOption) -> dict[str, object]:
    payload: dict[str, object] = {"id": str(row.id), "key": str(row.key), "label": str(row.label)}
    linked_card_count = getattr(row, "linked_card_count", None)
    if isinstance(linked_card_count, int):
        payload["linked_card_count"] = linked_card_count
    return payload


def symbol_option(symbol: Symbol) -> dict[str, object]:
    return {
        "id": symbol.id,
        "key": symbol.key,
        "label": symbol.label,
        "symbol_type": symbol.symbol_type,
        "text_token": symbol.text_token,
        "asset_url": _first_symbol_asset_url(symbol.reference_assets_json),
    }


def card_group_summary_payload(group: CardGroup, *, card_id: str | None = None) -> dict[str, object]:
    members = list(group.members.all())
    anchor_card_id = group.anchor_card.id
    card_ids = [member.card.id for member in members]
    position = next((member.position for member in members if member.card.id == card_id), None)
    return {
        "id": group.id,
        "key": group.key,
        "name": group.name,
        "anchor_card_id": anchor_card_id,
        "member_count": len(members),
        "card_ids": card_ids,
        "is_anchor": anchor_card_id == card_id,
        "position": position,
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
    q = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    query = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    card_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    max_confidence = serializers.FloatField(required=False, allow_null=True)
    keyword_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    keyword_match = serializers.ChoiceField(choices=['any', 'all'], required=False, allow_null=True)
    tag_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    tag_match = serializers.ChoiceField(choices=['any', 'all'], required=False, allow_null=True)
    mana_symbol_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    mana_symbol_match = serializers.ChoiceField(choices=['any', 'all'], required=False, allow_null=True)
    affinity_symbol_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    affinity_symbol_match = serializers.ChoiceField(choices=['any', 'all'], required=False, allow_null=True)
    devotion_symbol_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    devotion_symbol_match = serializers.ChoiceField(choices=['any', 'all'], required=False, allow_null=True)
    other_symbol_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    other_symbol_match = serializers.ChoiceField(choices=['any', 'all'], required=False, allow_null=True)
    symbol_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    type_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    type_match = serializers.ChoiceField(choices=['any', 'all'], required=False, allow_null=True)
    mana_cost_min = serializers.IntegerField(required=False, allow_null=True)
    mana_cost_max = serializers.IntegerField(required=False, allow_null=True)
    template_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_hero = serializers.BooleanField(required=False, allow_null=True)
    attack_min = serializers.IntegerField(required=False, allow_null=True)
    attack_max = serializers.IntegerField(required=False, allow_null=True)
    health_min = serializers.IntegerField(required=False, allow_null=True)
    health_max = serializers.IntegerField(required=False, allow_null=True)
    sort = serializers.ChoiceField(choices=CARD_SORT_VALUES, required=False, default=CARD_SORT_UPDATED_DESC)
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, default=DEFAULT_CARD_PAGE_SIZE)
    show_groups = serializers.BooleanField(required=False, default=False)

    def validated_filters(self) -> CardFilterParams:
        return {
            "query": self._query_or_none(),
            "card_ids": self._string_list_or_none("card_ids"),
            "max_confidence": self._float_or_none("max_confidence"),
            "keyword_ids": self._string_list_or_none("keyword_ids"),
            "keyword_match": self._string_or_none("keyword_match"),
            "tag_ids": self._string_list_or_none("tag_ids"),
            "tag_match": self._string_or_none("tag_match"),
            "mana_symbol_ids": self._string_list_or_none("mana_symbol_ids"),
            "mana_symbol_match": self._string_or_none("mana_symbol_match"),
            "affinity_symbol_ids": self._string_list_or_none("affinity_symbol_ids"),
            "affinity_symbol_match": self._string_or_none("affinity_symbol_match"),
            "devotion_symbol_ids": self._string_list_or_none("devotion_symbol_ids"),
            "devotion_symbol_match": self._string_or_none("devotion_symbol_match"),
            "other_symbol_ids": self._string_list_or_none("other_symbol_ids"),
            "other_symbol_match": self._string_or_none("other_symbol_match"),
            "symbol_ids": self._string_list_or_none("symbol_ids"),
            "type_ids": self._string_list_or_none("type_ids"),
            "type_match": self._string_or_none("type_match"),
            "mana_cost_min": self._int_or_none("mana_cost_min"),
            "mana_cost_max": self._int_or_none("mana_cost_max"),
            "template_id": self._string_or_none("template_id"),
            "is_hero": self._bool_or_none("is_hero"),
            "attack_min": self._int_or_none("attack_min"),
            "attack_max": self._int_or_none("attack_max"),
            "health_min": self._int_or_none("health_min"),
            "health_max": self._int_or_none("health_max"),
            "sort": self._sort_value("sort"),
        }

    def validated_list_filters(self) -> CardListFilterParams:
        filters = self.validated_filters()
        return {
            **filters,
            "page": self._required_int("page"),
            "page_size": self._required_int("page_size"),
            "show_groups": bool(self.validated_data.get("show_groups", False)),
        }

    def _query_or_none(self) -> str | None:
        return self._string_or_none("q") or self._string_or_none("query")

    def _string_or_none(self, key: str) -> str | None:
        value = self.validated_data.get(key)
        return value if isinstance(value, str) else None

    def _float_or_none(self, key: str) -> float | None:
        value = self.validated_data.get(key)
        return value if isinstance(value, float) else None

    def _int_or_none(self, key: str) -> int | None:
        value = self.validated_data.get(key)
        return value if isinstance(value, int) else None

    def _bool_or_none(self, key: str) -> bool | None:
        value = self.validated_data.get(key)
        return value if isinstance(value, bool) else None

    def _required_int(self, key: str) -> int:
        value = self.validated_data.get(key)
        return value if isinstance(value, int) else 0

    def _sort_value(self, key: str) -> CardSort:
        value = self.validated_data.get(key)
        return value if value in CARD_SORT_VALUES else CARD_SORT_UPDATED_DESC

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
    is_hero = serializers.BooleanField(required=False)
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
        if "is_hero" in self.validated_data:
            updates["is_hero"] = self.validated_data["is_hero"]
        for field_name in ("keyword_ids", "tag_ids", "type_ids", "symbol_ids"):
            if field_name in self.validated_data:
                updates[field_name] = self.validated_data[field_name]
        return updates


class LatestCardReparseSerializer(serializers.Serializer[dict[str, object]]):
    template_id = serializers.CharField(required=False, allow_blank=False)


def _validated_names(values: list[str], allowed: set[str], message: str) -> list[str]:
    if not all(value in allowed for value in values):
        raise serializers.ValidationError(message)
    return values
