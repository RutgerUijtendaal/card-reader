from __future__ import annotations

from pathlib import Path

from django.db import transaction

from card_reader_core.models import Card, CardVersion, ImportJobItem, ImportJobStatus, ParseResult, now_utc

from ..helpers import extract_mana_symbols, normalize_slug_key, to_int_or_none
from ..metadata_repository import (
    replace_card_version_keywords,
    replace_card_version_symbols,
    replace_card_version_tags,
    replace_card_version_types,
)
from .images import save_image_record
from .queries import get_card, get_latest_card_version
from .snapshots import (
    DEFAULT_FIELD_SOURCES,
    FIELD_SOURCE_AUTO,
    FIELD_SOURCE_MANUAL,
    SCALAR_FIELD_NAMES,
    apply_scalar_value,
    build_parsed_snapshot,
    decode_field_sources,
    decode_parsed_snapshot,
    restore_metadata_group_from_snapshot,
    string_list,
)


def save_parsed_card(
    *,
    item: ImportJobItem,
    template_id: str,
    checksum: str,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
    raw_ocr: dict[str, object],
    keyword_ids: list[str] | None = None,
    tag_ids: list[str] | None = None,
    type_ids: list[str] | None = None,
    symbol_ids: list[str] | None = None,
    reparse_existing: bool = True,
) -> CardVersion:
    parsed_name = normalized_fields.get("name", "").strip() or Path(item.source_file).stem
    card_key = normalize_slug_key(parsed_name)

    with transaction.atomic():
        existing_version = None
        if reparse_existing:
            existing_version = (
                CardVersion.objects.filter(image_hash=checksum, is_latest=True)
                .order_by("-updated_at")
                .first()
            )
        if existing_version is not None:
            return update_existing_version(
                item,
                existing_version,
                normalized_fields,
                confidence,
                raw_ocr,
                keyword_ids=keyword_ids or [],
                tag_ids=tag_ids or [],
                type_ids=type_ids or [],
                symbol_ids=symbol_ids or [],
            )

        card = Card.objects.filter(key=card_key).first()
        if card is None:
            card = Card.objects.create(key=card_key, label=parsed_name)

        latest = get_latest_card_version(card.id)
        if latest and latest.image_hash == checksum and reparse_existing:
            return update_existing_version(
                item,
                latest,
                normalized_fields,
                confidence,
                raw_ocr,
                keyword_ids=keyword_ids or [],
                tag_ids=tag_ids or [],
                type_ids=type_ids or [],
                symbol_ids=symbol_ids or [],
            )

        version = create_new_version(item, card, template_id, checksum, normalized_fields, confidence)
        replace_card_version_keywords(card_version_id=version.id, keyword_ids=keyword_ids or [])
        replace_card_version_tags(card_version_id=version.id, tag_ids=tag_ids or [])
        replace_card_version_types(card_version_id=version.id, type_ids=type_ids or [])
        replace_card_version_symbols(card_version_id=version.id, symbol_ids=symbol_ids or [])
        save_parse_result(version, raw_ocr, normalized_fields, confidence)
        save_parsed_snapshot(
            version,
            normalized_fields=normalized_fields,
            keyword_ids=keyword_ids or [],
            tag_ids=tag_ids or [],
            type_ids=type_ids or [],
            symbol_ids=symbol_ids or [],
        )
        save_image_record(version, item.source_file, checksum)
        mark_item_completed(item)

        card.label = parsed_name
        card.latest_version = version
        card.updated_at = now_utc()
        card.save(update_fields=["label", "latest_version", "updated_at"])
        return version


def update_latest_card_version(
    *,
    card_id: str,
    updates: dict[str, object],
    restore_fields: list[str],
    restore_metadata_groups: list[str],
    unlock_fields: list[str],
    unlock_metadata_groups: list[str],
) -> tuple[Card, CardVersion] | None:
    card = get_card(card_id)
    version = get_latest_card_version(card_id)
    if card is None or version is None:
        return None

    snapshot = decode_parsed_snapshot(version.parsed_snapshot_json)
    field_sources = decode_field_sources(version.field_sources_json)

    with transaction.atomic():
        restored_name = False
        for field_name in unlock_fields:
            if field_name in field_sources["fields"]:
                field_sources["fields"][field_name] = FIELD_SOURCE_AUTO
        for group_name in unlock_metadata_groups:
            if group_name in field_sources["metadata"]:
                field_sources["metadata"][group_name] = FIELD_SOURCE_AUTO

        for field_name in restore_fields:
            if field_name not in field_sources["fields"]:
                continue
            apply_scalar_value(version, field_name, snapshot["fields"].get(field_name))
            field_sources["fields"][field_name] = FIELD_SOURCE_AUTO
            if field_name == "name":
                restored_name = True
        for group_name in restore_metadata_groups:
            if group_name not in field_sources["metadata"]:
                continue
            restore_metadata_group_from_snapshot(version.id, group_name, snapshot)
            field_sources["metadata"][group_name] = FIELD_SOURCE_AUTO

        for field_name in SCALAR_FIELD_NAMES:
            if field_name not in updates:
                continue
            apply_scalar_value(version, field_name, updates[field_name])
            field_sources["fields"][field_name] = FIELD_SOURCE_MANUAL
            if field_name == "name":
                restored_name = True

        if "keyword_ids" in updates:
            replace_card_version_keywords(
                card_version_id=version.id,
                keyword_ids=string_list(updates.get("keyword_ids")),
            )
            field_sources["metadata"]["keywords"] = FIELD_SOURCE_MANUAL
        if "tag_ids" in updates:
            replace_card_version_tags(
                card_version_id=version.id,
                tag_ids=string_list(updates.get("tag_ids")),
            )
            field_sources["metadata"]["tags"] = FIELD_SOURCE_MANUAL
        if "type_ids" in updates:
            replace_card_version_types(
                card_version_id=version.id,
                type_ids=string_list(updates.get("type_ids")),
            )
            field_sources["metadata"]["types"] = FIELD_SOURCE_MANUAL
        if "symbol_ids" in updates:
            replace_card_version_symbols(
                card_version_id=version.id,
                symbol_ids=string_list(updates.get("symbol_ids")),
            )
            field_sources["metadata"]["symbols"] = FIELD_SOURCE_MANUAL

        if restored_name or "name" in updates:
            card.label = version.name
            card.key = normalize_slug_key(version.name)
            card.updated_at = now_utc()
            card.save(update_fields=["label", "key", "updated_at"])

        version.mana_symbols_json = extract_mana_symbols({"mana_cost": version.mana_cost})
        version.field_sources_json = field_sources
        version.updated_at = now_utc()
        version.save()
        return card, version


def apply_parsed_fields_to_version(
    version: CardVersion,
    *,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
) -> None:
    version.name = normalized_fields.get("name", "")
    version.type_line = normalized_fields.get("type_line", "")
    version.mana_cost = normalized_fields.get("mana_cost", "")
    version.mana_symbols_json = extract_mana_symbols(normalized_fields)
    version.attack = to_int_or_none(normalized_fields.get("attack"))
    version.health = to_int_or_none(normalized_fields.get("health"))
    version.rules_text = normalized_fields.get("rules_text", "")
    version.confidence = float(confidence.get("overall", 0.0))


def update_existing_version(
    item: ImportJobItem,
    version: CardVersion,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
    raw_ocr: dict[str, object],
    *,
    keyword_ids: list[str],
    tag_ids: list[str],
    type_ids: list[str],
    symbol_ids: list[str],
) -> CardVersion:
    previous_name = version.name
    apply_parsed_output_to_version(
        version,
        normalized_fields=normalized_fields,
        confidence=confidence,
        keyword_ids=keyword_ids,
        tag_ids=tag_ids,
        type_ids=type_ids,
        symbol_ids=symbol_ids,
    )
    save_parse_result(version, raw_ocr, normalized_fields, confidence)
    save_parsed_snapshot(
        version,
        normalized_fields=normalized_fields,
        keyword_ids=keyword_ids,
        tag_ids=tag_ids,
        type_ids=type_ids,
        symbol_ids=symbol_ids,
    )
    version.updated_at = now_utc()
    version.save()
    if version.name != previous_name:
        card = Card.objects.filter(id=version.card.id).first()
        if card is not None:
            card.label = version.name
            card.key = normalize_slug_key(version.name)
            card.updated_at = now_utc()
            card.save(update_fields=["label", "key", "updated_at"])
    mark_item_completed(item)
    return version


def create_new_version(
    item: ImportJobItem,
    card: Card,
    template_id: str,
    checksum: str,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
) -> CardVersion:
    latest = get_latest_card_version(card.id)
    previous_version_id = None
    version_number = 1
    if latest is not None:
        latest.is_latest = False
        latest.updated_at = now_utc()
        latest.save(update_fields=["is_latest", "updated_at"])
        previous_version_id = latest.id
        version_number = latest.version_number + 1

    return CardVersion.objects.create(
        card=card,
        version_number=version_number,
        template_id=template_id,
        image_hash=checksum,
        name=normalized_fields.get("name", "").strip() or Path(item.source_file).stem,
        type_line=normalized_fields.get("type_line", ""),
        mana_cost=normalized_fields.get("mana_cost", ""),
        mana_symbols_json=extract_mana_symbols(normalized_fields),
        attack=to_int_or_none(normalized_fields.get("attack")),
        health=to_int_or_none(normalized_fields.get("health")),
        rules_text=normalized_fields.get("rules_text", ""),
        confidence=float(confidence.get("overall", 0.0)),
        field_sources_json=DEFAULT_FIELD_SOURCES,
        parsed_snapshot_json=build_parsed_snapshot(normalized_fields, [], [], [], []),
        is_latest=True,
        previous_version_id=previous_version_id,
    )


def save_parse_result(
    version: CardVersion,
    raw_ocr: dict[str, object],
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
) -> None:
    parse_result = ParseResult.objects.create(
        card_version=version,
        raw_ocr_json=raw_ocr,
        normalized_fields_json=normalized_fields,
        confidence_json=confidence,
    )
    version.parse_result = parse_result
    version.save(update_fields=["parse_result"])


def save_parsed_snapshot(
    version: CardVersion,
    *,
    normalized_fields: dict[str, str],
    keyword_ids: list[str],
    tag_ids: list[str],
    type_ids: list[str],
    symbol_ids: list[str],
) -> None:
    version.parsed_snapshot_json = build_parsed_snapshot(
        normalized_fields,
        keyword_ids,
        tag_ids,
        type_ids,
        symbol_ids,
    )
    version.save(update_fields=["parsed_snapshot_json"])


def mark_item_completed(item: ImportJobItem) -> None:
    item.status = ImportJobStatus.completed
    item.error_message = None
    item.updated_at = now_utc()
    item.save(update_fields=["status", "error_message", "updated_at"])


def apply_parsed_output_to_version(
    version: CardVersion,
    *,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
    keyword_ids: list[str],
    tag_ids: list[str],
    type_ids: list[str],
    symbol_ids: list[str],
) -> None:
    field_sources = decode_field_sources(version.field_sources_json)
    if field_sources["fields"]["name"] == FIELD_SOURCE_AUTO:
        version.name = normalized_fields.get("name", "")
    if field_sources["fields"]["type_line"] == FIELD_SOURCE_AUTO:
        version.type_line = normalized_fields.get("type_line", "")
    if field_sources["fields"]["mana_cost"] == FIELD_SOURCE_AUTO:
        version.mana_cost = normalized_fields.get("mana_cost", "")
        version.mana_symbols_json = extract_mana_symbols(normalized_fields)
    if field_sources["fields"]["attack"] == FIELD_SOURCE_AUTO:
        version.attack = to_int_or_none(normalized_fields.get("attack"))
    if field_sources["fields"]["health"] == FIELD_SOURCE_AUTO:
        version.health = to_int_or_none(normalized_fields.get("health"))
    if field_sources["fields"]["rules_text"] == FIELD_SOURCE_AUTO:
        version.rules_text = normalized_fields.get("rules_text", "")

    if field_sources["metadata"]["keywords"] == FIELD_SOURCE_AUTO:
        replace_card_version_keywords(card_version_id=version.id, keyword_ids=keyword_ids)
    if field_sources["metadata"]["tags"] == FIELD_SOURCE_AUTO:
        replace_card_version_tags(card_version_id=version.id, tag_ids=tag_ids)
    if field_sources["metadata"]["types"] == FIELD_SOURCE_AUTO:
        replace_card_version_types(card_version_id=version.id, type_ids=type_ids)
    if field_sources["metadata"]["symbols"] == FIELD_SOURCE_AUTO:
        replace_card_version_symbols(card_version_id=version.id, symbol_ids=symbol_ids)

    version.confidence = float(confidence.get("overall", 0.0))
