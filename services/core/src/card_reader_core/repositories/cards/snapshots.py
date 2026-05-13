from __future__ import annotations

import json
from typing import cast

from card_reader_core.models import CardVersion

from ..helpers import to_int_or_none
from ..metadata_repository import (
    replace_card_version_keywords,
    replace_card_version_symbols,
    replace_card_version_tags,
    replace_card_version_types,
)
from .types import FieldSourcesPayload, ParsedSnapshotPayload

DEFAULT_FIELD_SOURCES = {
    "fields": {
        "name": "auto",
        "type_line": "auto",
        "mana_cost": "auto",
        "attack": "auto",
        "health": "auto",
        "rules_text": "auto",
    },
    "metadata": {
        "keywords": "auto",
        "tags": "auto",
        "types": "auto",
        "symbols": "auto",
    },
}

FIELD_SOURCE_AUTO = "auto"
FIELD_SOURCE_MANUAL = "manual"
SCALAR_FIELD_NAMES = ("name", "type_line", "mana_cost", "attack", "health", "rules_text")
METADATA_GROUP_NAMES = ("keywords", "tags", "types", "symbols")


def decode_field_sources(raw: object) -> FieldSourcesPayload:
    default: FieldSourcesPayload = {
        "fields": dict(DEFAULT_FIELD_SOURCES["fields"]),
        "metadata": dict(DEFAULT_FIELD_SOURCES["metadata"]),
    }
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return default
    if not isinstance(raw, dict):
        return default

    fields = raw.get("fields")
    metadata = raw.get("metadata")
    if isinstance(fields, dict):
        for field_name in SCALAR_FIELD_NAMES:
            value = fields.get(field_name)
            if value in {FIELD_SOURCE_AUTO, FIELD_SOURCE_MANUAL}:
                default["fields"][field_name] = cast(str, value)
    if isinstance(metadata, dict):
        for group_name in METADATA_GROUP_NAMES:
            value = metadata.get(group_name)
            if value in {FIELD_SOURCE_AUTO, FIELD_SOURCE_MANUAL}:
                default["metadata"][group_name] = cast(str, value)
    return default


def decode_parsed_snapshot(raw: object) -> ParsedSnapshotPayload:
    default: ParsedSnapshotPayload = {
        "fields": {
            "name": "",
            "type_line": "",
            "mana_cost": "",
            "attack": None,
            "health": None,
            "rules_text": "",
        },
        "metadata": {
            "keyword_ids": [],
            "tag_ids": [],
            "type_ids": [],
            "symbol_ids": [],
        },
    }
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return default
    if not isinstance(raw, dict):
        return default

    fields = raw.get("fields")
    metadata = raw.get("metadata")
    if isinstance(fields, dict):
        for field_name in SCALAR_FIELD_NAMES:
            if field_name in fields:
                default["fields"][field_name] = fields[field_name]
    if isinstance(metadata, dict):
        for key in ("keyword_ids", "tag_ids", "type_ids", "symbol_ids"):
            value = metadata.get(key)
            if isinstance(value, list):
                default["metadata"][key] = [str(item) for item in value]
    return default


def build_parsed_snapshot(
    normalized_fields: dict[str, str],
    keyword_ids: list[str],
    tag_ids: list[str],
    type_ids: list[str],
    symbol_ids: list[str],
) -> ParsedSnapshotPayload:
    return {
        "fields": {
            "name": normalized_fields.get("name", ""),
            "type_line": normalized_fields.get("type_line", ""),
            "mana_cost": normalized_fields.get("mana_cost", ""),
            "attack": to_int_or_none(normalized_fields.get("attack")),
            "health": to_int_or_none(normalized_fields.get("health")),
            "rules_text": normalized_fields.get("rules_text_enriched", normalized_fields.get("rules_text", "")),
        },
        "metadata": {
            "keyword_ids": keyword_ids,
            "tag_ids": tag_ids,
            "type_ids": type_ids,
            "symbol_ids": symbol_ids,
        },
    }


def apply_scalar_value(version: CardVersion, field_name: str, value: object) -> None:
    if field_name == "name":
        version.name = str(value or "").strip()
        return
    if field_name == "type_line":
        version.type_line = str(value or "")
        return
    if field_name == "mana_cost":
        version.mana_cost = str(value or "")
        return
    if field_name == "rules_text":
        version.rules_text = str(value or "")
        return
    if field_name == "attack":
        version.attack = coerce_optional_int(value)
        return
    if field_name == "health":
        version.health = coerce_optional_int(value)


def coerce_optional_int(value: object) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def restore_metadata_group_from_snapshot(
    card_version_id: str,
    group_name: str,
    snapshot: ParsedSnapshotPayload,
) -> None:
    metadata = snapshot.get("metadata", {})
    if group_name == "keywords":
        replace_card_version_keywords(
            card_version_id=card_version_id,
            keyword_ids=string_list(metadata.get("keyword_ids")),
        )
    elif group_name == "tags":
        replace_card_version_tags(
            card_version_id=card_version_id,
            tag_ids=string_list(metadata.get("tag_ids")),
        )
    elif group_name == "types":
        replace_card_version_types(
            card_version_id=card_version_id,
            type_ids=string_list(metadata.get("type_ids")),
        )
    elif group_name == "symbols":
        replace_card_version_symbols(
            card_version_id=card_version_id,
            symbol_ids=string_list(metadata.get("symbol_ids")),
        )


def string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]
