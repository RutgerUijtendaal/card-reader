from __future__ import annotations
from typing import TYPE_CHECKING, cast

from rest_framework import serializers

from card_reader_api.cards.public_urls import card_image_asset_url
from card_reader_api.common.serializer_values import ValidatedStringValuesMixin
from card_reader_core.metadata import MANA_FAMILIES
from card_reader_core.models import (
    CARD_POOLS,
    CARD_FACTIONS,
    CARD_ROLE_FILTER_VALUES,
    CARD_ROLES,
    CARD_LIFECYCLE_FILTER_VALUES,
    CARD_LIFECYCLE_STATUSES,
    DEFAULT_CARD_LIFECYCLE_FILTER,
    Card,
    CardPool,
    CardFaction,
    CardLifecycleFilter,
    CardVersion,
    CardRoleFilter,
    Keyword,
    Symbol,
    Tag,
    Type,
    card_role_keys,
    card_faction_keys,
    card_mana_family_keys,
    normalize_card_lifecycle_filter,
)
from card_reader_core.repositories.cards import DEFAULT_CARD_PAGE_SIZE, CardListRow
from card_reader_core.repositories.cards import (
    CARD_SORT_DEFAULT,
    CARD_SORT_TYPES_ASC,
    CARD_SORT_UPDATED_DESC,
    CARD_SORT_VALUES,
    CardFilterParams,
    CardSort,
)
from card_reader_core.rules import render_enriched_rule_text
from card_reader_core.services.decks import normalize_deck_building_config

if TYPE_CHECKING:
    from card_reader_core.models import CardGroup, Deck
    from card_reader_core.services.cards import CardEditState, CardMetadata

MANA_FAMILY_KEYS = tuple(family.key for family in MANA_FAMILIES)
MetadataOption = Keyword | Tag | Type
SCALAR_FIELDS = {"name", "type_line", "mana_cost", "attack", "health", "rules_text"}
METADATA_GROUPS = {"keywords", "tags", "types", "symbols"}


class CardListFilterParams(CardFilterParams):
    page: int
    page_size: int
    show_groups: bool


class CardFilterMetadataScopeSerializer(serializers.Serializer[dict[str, object]]):
    card_pool = serializers.ChoiceField(choices=CARD_POOLS, required=False)

    def requested_card_pool(self) -> CardPool | None:
        value = self.validated_data.get("card_pool")
        return cast(CardPool, value) if isinstance(value, str) else None


def card_payload(
    card: Card,
    version: CardVersion,
    *,
    image_url: str | None,
    metadata: CardMetadata | None = None,
    edit_state: CardEditState | None = None,
    card_groups: list[dict[str, object]] | None = None,
    deck_references: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    rendered_rule_text = _render_card_rule_text(version, metadata)
    payload: dict[str, object] = {
        "id": card.id,
        "result_type": "card",
        "key": card.key,
        "label": card.label,
        "name": version.name,
        "card_pool": card.card_pool,
        "card_roles": list(card_role_keys(card)),
        "card_factions": list(card_faction_keys(card)),
        "card_mana_families": list(card_mana_family_keys(card)),
        "deck_building_config": normalize_deck_building_config(card.deck_building_config_json),
        "lifecycle_status": card.lifecycle_status,
        "template_id": version.template.key,
        "version_id": version.id,
        "version_number": version.version_number,
        "previous_version_id": version.previous_version.id
        if version.previous_version is not None
        else None,
        "is_latest": version.is_latest,
        "content_version": _content_version_payload(version),
        "type_line": version.type_line,
        "mana_cost": version.mana_cost,
        "mana_symbols": _decode_mana_symbols(version.mana_symbols_json),
        "mana_value": version.mana_value,
        "mana_family_sort_key": card.mana_family_sort_key,
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
        "deck_references": deck_references or [],
    }
    if metadata is not None:
        payload.update(metadata_payload(metadata))
    if edit_state is not None:
        payload.update(edit_state_payload(edit_state))
    return payload


def card_list_row_payload(row: CardListRow) -> dict[str, object]:
    return card_payload(
        row.version.card,
        row.version,
        image_url=card_image_asset_url(
            row.image,
            fallback_url=f"/cards/{row.version.card.id}/image",
        ),
        metadata={
            "keywords": row.keywords,
            "tags": row.tags,
            "symbols": row.symbols,
            "types": row.types,
        },
    )


def _content_version_payload(version: CardVersion) -> dict[str, object] | None:
    content_version = version.content_version
    if content_version is None:
        return None
    return {
        "id": content_version.id,
        "version_number": content_version.version_number,
        "base_version": content_version.base_version,
        "description": content_version.description,
    }


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


def card_group_summary_payload(
    group: CardGroup,
    *,
    card_id: str | None = None,
) -> dict[str, object]:
    members = list(group.members.all())
    anchor_card_id = group.anchor_card.id
    card_ids = [member.card.id for member in members]
    position = next((member.position for member in members if member.card.id == card_id), None)
    return {
        "id": group.id,
        "key": group.key,
        "name": group.name,
        "card_pool": group.anchor_card.card_pool,
        "anchor_card_id": anchor_card_id,
        "member_count": len(members),
        "card_ids": card_ids,
        "is_anchor": anchor_card_id == card_id,
        "position": position,
    }


def card_deck_reference_payload(deck: Deck, *, card_id: str) -> dict[str, object]:
    mainboard_quantity = sum(
        int(entry.quantity) for entry in deck.entries.all() if entry.card.id == card_id
    )
    sideboard_quantity = sum(
        int(entry.quantity)
        for sideboard in deck.sideboards.all()
        for entry in sideboard.entries.all()
        if entry.card.id == card_id
    )
    return {
        "as_hero": deck.hero_card.id == card_id,
        "mainboard_quantity": mainboard_quantity,
        "sideboard_quantity": sideboard_quantity,
    }


def _render_card_rule_text(version: CardVersion, metadata: CardMetadata | None) -> str:
    if not version.rules_text_enriched:
        return version.rules_text
    if metadata is None:
        return version.rules_text
    symbol_tokens_by_key = {symbol.key: symbol.text_token for symbol in metadata["symbols"]}
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


class CardFiltersQuerySerializer(
    ValidatedStringValuesMixin,
    serializers.Serializer[dict[str, object]],
):
    q = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    query = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    card_ids = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    max_confidence = serializers.FloatField(required=False, allow_null=True)
    keyword_ids = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    keyword_match = serializers.ChoiceField(choices=["any", "all"], required=False, allow_null=True)
    tag_ids = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    tag_match = serializers.ChoiceField(choices=["any", "all"], required=False, allow_null=True)
    mana_symbol_ids = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    mana_symbol_exclude_ids = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    mana_symbol_match = serializers.ChoiceField(
        choices=["any", "all"], required=False, allow_null=True
    )
    mana_family_keys = serializers.ListField(
        child=serializers.ChoiceField(choices=MANA_FAMILY_KEYS),
        required=False,
        allow_empty=True,
    )
    mana_family_exclude_keys = serializers.ListField(
        child=serializers.ChoiceField(choices=MANA_FAMILY_KEYS),
        required=False,
        allow_empty=True,
    )
    mana_family_match = serializers.ChoiceField(
        choices=["any", "all"], required=False, allow_null=True
    )
    affinity_symbol_ids = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    affinity_symbol_exclude_ids = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    affinity_symbol_match = serializers.ChoiceField(
        choices=["any", "all"], required=False, allow_null=True
    )
    devotion_symbol_ids = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    devotion_symbol_exclude_ids = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    devotion_symbol_match = serializers.ChoiceField(
        choices=["any", "all"], required=False, allow_null=True
    )
    other_symbol_ids = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    other_symbol_exclude_ids = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    other_symbol_match = serializers.ChoiceField(
        choices=["any", "all"], required=False, allow_null=True
    )
    symbol_ids = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    type_ids = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    type_exclude_ids = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    type_match = serializers.ChoiceField(choices=["any", "all"], required=False, allow_null=True)
    mana_cost_min = serializers.IntegerField(required=False, allow_null=True)
    mana_cost_max = serializers.IntegerField(required=False, allow_null=True)
    template_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    card_pool = serializers.ChoiceField(choices=CARD_POOLS, required=False)
    card_roles = serializers.ListField(
        child=serializers.ChoiceField(choices=CARD_ROLE_FILTER_VALUES),
        required=False,
        allow_empty=True,
    )
    card_role_exclude = serializers.ListField(
        child=serializers.ChoiceField(choices=CARD_ROLE_FILTER_VALUES),
        required=False,
        allow_empty=True,
    )
    card_role_match = serializers.ChoiceField(choices=["any", "all"], required=False, default="any")
    card_factions = serializers.ListField(
        child=serializers.ChoiceField(choices=CARD_FACTIONS),
        required=False,
        allow_empty=True,
    )
    card_faction_exclude = serializers.ListField(
        child=serializers.ChoiceField(choices=CARD_FACTIONS),
        required=False,
        allow_empty=True,
    )
    card_faction_match = serializers.ChoiceField(
        choices=["any", "all"], required=False, default="any"
    )
    attack_min = serializers.IntegerField(required=False, allow_null=True)
    attack_max = serializers.IntegerField(required=False, allow_null=True)
    health_min = serializers.IntegerField(required=False, allow_null=True)
    health_max = serializers.IntegerField(required=False, allow_null=True)
    lifecycle_status = serializers.ChoiceField(
        choices=CARD_LIFECYCLE_FILTER_VALUES,
        required=False,
        default=DEFAULT_CARD_LIFECYCLE_FILTER,
    )
    sort = serializers.ChoiceField(choices=CARD_SORT_VALUES, required=False)
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(
        required=False, min_value=1, default=DEFAULT_CARD_PAGE_SIZE
    )
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
            "mana_symbol_exclude_ids": self._string_list_or_none("mana_symbol_exclude_ids"),
            "mana_symbol_match": self._string_or_none("mana_symbol_match"),
            "mana_family_keys": self._string_list_or_none("mana_family_keys"),
            "mana_family_exclude_keys": self._string_list_or_none("mana_family_exclude_keys"),
            "mana_family_match": self._string_or_none("mana_family_match"),
            "affinity_symbol_ids": self._string_list_or_none("affinity_symbol_ids"),
            "affinity_symbol_exclude_ids": self._string_list_or_none("affinity_symbol_exclude_ids"),
            "affinity_symbol_match": self._string_or_none("affinity_symbol_match"),
            "devotion_symbol_ids": self._string_list_or_none("devotion_symbol_ids"),
            "devotion_symbol_exclude_ids": self._string_list_or_none("devotion_symbol_exclude_ids"),
            "devotion_symbol_match": self._string_or_none("devotion_symbol_match"),
            "other_symbol_ids": self._string_list_or_none("other_symbol_ids"),
            "other_symbol_exclude_ids": self._string_list_or_none("other_symbol_exclude_ids"),
            "other_symbol_match": self._string_or_none("other_symbol_match"),
            "symbol_ids": self._string_list_or_none("symbol_ids"),
            "type_ids": self._string_list_or_none("type_ids"),
            "type_exclude_ids": self._string_list_or_none("type_exclude_ids"),
            "type_match": self._string_or_none("type_match"),
            "mana_cost_min": self._int_or_none("mana_cost_min"),
            "mana_cost_max": self._int_or_none("mana_cost_max"),
            "template_id": self._string_or_none("template_id"),
            "card_pool": cast(
                CardPool | None,
                self.validated_data.get("card_pool"),
            ),
            "card_roles": cast(
                list[CardRoleFilter] | None, self._string_list_or_none("card_roles")
            ),
            "card_role_exclude": cast(
                list[CardRoleFilter] | None,
                self._string_list_or_none("card_role_exclude"),
            ),
            "card_role_match": self.validated_data.get("card_role_match", "any"),
            "card_factions": cast(
                list[CardFaction] | None,
                self._string_list_or_none("card_factions"),
            ),
            "card_faction_exclude": cast(
                list[CardFaction] | None,
                self._string_list_or_none("card_faction_exclude"),
            ),
            "card_faction_match": self.validated_data.get("card_faction_match", "any"),
            "attack_min": self._int_or_none("attack_min"),
            "attack_max": self._int_or_none("attack_max"),
            "health_min": self._int_or_none("health_min"),
            "health_max": self._int_or_none("health_max"),
            "lifecycle_status": self._lifecycle_status_value("lifecycle_status"),
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

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if attrs.get("card_pool") is None and attrs.get("sort") in {
            CARD_SORT_DEFAULT,
            CARD_SORT_TYPES_ASC,
        }:
            raise serializers.ValidationError(
                {"sort": "This sort requires an explicit card_pool."}
            )
        roles = attrs.get("card_roles")
        if attrs.get("card_role_match") == "all" and isinstance(roles, list):
            if "standard" in roles and len(set(roles)) > 1:
                raise serializers.ValidationError(
                    {"card_roles": "Normal cannot be combined with other roles when matching all."}
                )
        return attrs

    def _query_or_none(self) -> str | None:
        return self._string_or_none("q") or self._string_or_none("query")

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
        if value in CARD_SORT_VALUES:
            return cast(CardSort, value)
        if self.validated_data.get("card_pool") is None:
            return CARD_SORT_UPDATED_DESC
        return CARD_SORT_DEFAULT

    def _lifecycle_status_value(self, key: str) -> CardLifecycleFilter:
        value = self.validated_data.get(key)
        return normalize_card_lifecycle_filter(value)

class LatestVersionUpdateSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField(required=False, allow_blank=False)
    type_line = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    mana_cost = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    attack = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    health = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    rules_text = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=False,
    )
    rules_text_enriched = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=False,
    )
    card_pool = serializers.ChoiceField(choices=CARD_POOLS, required=False)
    card_roles = serializers.ListField(
        child=serializers.ChoiceField(choices=CARD_ROLES),
        required=False,
        allow_empty=True,
    )
    card_factions = serializers.ListField(
        child=serializers.ChoiceField(choices=CARD_FACTIONS),
        required=False,
        allow_empty=True,
    )
    card_mana_families = serializers.ListField(
        child=serializers.ChoiceField(choices=MANA_FAMILY_KEYS),
        required=False,
        allow_empty=True,
    )
    deck_building_config = serializers.JSONField(required=False)
    lifecycle_status = serializers.ChoiceField(choices=CARD_LIFECYCLE_STATUSES, required=False)
    keyword_ids = serializers.ListField(child=serializers.CharField(), required=False)
    tag_ids = serializers.ListField(child=serializers.CharField(), required=False)
    type_ids = serializers.ListField(child=serializers.CharField(), required=False)
    symbol_ids = serializers.ListField(child=serializers.CharField(), required=False)
    restore_fields = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    restore_metadata_groups = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    unlock_fields = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    unlock_metadata_groups = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )

    def validate_restore_fields(self, value: list[str]) -> list[str]:
        return _validated_names(value, SCALAR_FIELDS, "Invalid scalar field name.")

    def validate_unlock_fields(self, value: list[str]) -> list[str]:
        return _validated_names(value, SCALAR_FIELDS, "Invalid scalar field name.")

    def validate_restore_metadata_groups(self, value: list[str]) -> list[str]:
        return _validated_names(value, METADATA_GROUPS, "Invalid metadata group name.")

    def validate_unlock_metadata_groups(self, value: list[str]) -> list[str]:
        return _validated_names(value, METADATA_GROUPS, "Invalid metadata group name.")

    def validate_deck_building_config(self, value: object) -> dict[str, object]:
        try:
            return normalize_deck_building_config(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validated_update_payload(self) -> dict[str, object]:
        updates: dict[str, object] = {}
        for field_name in SCALAR_FIELDS:
            if field_name in self.validated_data:
                updates[field_name] = self.validated_data[field_name]
        if "rules_text_enriched" in self.validated_data:
            updates["rules_text"] = self.validated_data["rules_text_enriched"]
        if "card_pool" in self.validated_data:
            updates["card_pool"] = self.validated_data["card_pool"]
        if "card_roles" in self.validated_data:
            updates["card_roles"] = self.validated_data["card_roles"]
        if "card_factions" in self.validated_data:
            updates["card_factions"] = self.validated_data["card_factions"]
        if "card_mana_families" in self.validated_data:
            updates["card_mana_families"] = self.validated_data["card_mana_families"]
        if "deck_building_config" in self.validated_data:
            updates["deck_building_config"] = self.validated_data["deck_building_config"]
        if "lifecycle_status" in self.validated_data:
            updates["lifecycle_status"] = self.validated_data["lifecycle_status"]
        for field_name in ("keyword_ids", "tag_ids", "type_ids", "symbol_ids"):
            if field_name in self.validated_data:
                updates[field_name] = self.validated_data[field_name]
        return updates


class LatestCardReparseSerializer(serializers.Serializer[dict[str, object]]):
    template_id = serializers.CharField(required=False, allow_blank=False)


class CardVersionParseFlagItemSerializer(serializers.Serializer[dict[str, object]]):
    property_key = serializers.ChoiceField(
        choices=[
            "name",
            "type_line",
            "mana_cost",
            "attack",
            "health",
            "rules_text",
            "keywords",
            "tags",
            "types",
            "symbols",
            "overall",
            "other",
        ]
    )
    expected_value = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class CardVersionParseFlagCreateSerializer(serializers.Serializer[dict[str, object]]):
    note = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    items = CardVersionParseFlagItemSerializer(many=True, allow_empty=False)

    def validate_items(self, value: list[dict[str, object]]) -> list[dict[str, object]]:
        for item in value:
            if item.get("property_key") == "overall":
                note = item.get("note")
                if not isinstance(note, str) or not note.strip():
                    raise serializers.ValidationError("Overall suggestions require a note.")
                continue
            expected_value = item.get("expected_value")
            if not isinstance(expected_value, str) or not expected_value.strip():
                raise serializers.ValidationError(
                    "Property flag suggestions require an expected value."
                )
        return value


def _validated_names(values: list[str], allowed: set[str], message: str) -> list[str]:
    if not all(value in allowed for value in values):
        raise serializers.ValidationError(message)
    return values
    card_role_keys,
