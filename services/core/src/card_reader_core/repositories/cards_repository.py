from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from django.db import transaction
from django.db.models import Prefetch, QuerySet

from ..storage import relativize_storage_path, resolve_storage_path, store_image
from .helpers import extract_mana_symbols, normalize_slug_key, to_int_or_none
from .metadata_repository import (
    replace_card_version_keywords,
    replace_card_version_symbols,
    replace_card_version_tags,
    replace_card_version_types,
)
from card_reader_core.models import (
    Card,
    CardVersion,
    CardVersionImage,
    CardVersionKeyword,
    CardVersionSymbol,
    CardVersionTag,
    CardVersionType,
    ImportJobItem,
    ImportJobStatus,
    ParseResult,
    Keyword,
    Symbol,
    Tag,
    Type,
    now_utc,
)
from card_reader_core.search.cards import apply_card_search


@dataclass(frozen=True)
class LatestCardVersionReparseSource:
    card_version_id: str
    template_id: str
    image_path: Path


@dataclass(frozen=True)
class CardListRow:
    version: CardVersion
    image: CardVersionImage | None
    keywords: list[Keyword]
    tags: list[Tag]
    symbols: list[Symbol]
    types: list[Type]


@dataclass(frozen=True)
class PaginatedCardList:
    count: int
    page: int
    page_size: int
    results: list[CardListRow]


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


class FieldSourcesPayload(TypedDict):
    fields: dict[str, str]
    metadata: dict[str, str]


class ParsedSnapshotPayload(TypedDict):
    fields: dict[str, Any]
    metadata: dict[str, list[str]]


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
            return _update_existing_version(
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
            return _update_existing_version(
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

        version = _create_new_version(item, card, template_id, checksum, normalized_fields, confidence)
        replace_card_version_keywords(card_version_id=version.id, keyword_ids=keyword_ids or [])
        replace_card_version_tags(card_version_id=version.id, tag_ids=tag_ids or [])
        replace_card_version_types(card_version_id=version.id, type_ids=type_ids or [])
        replace_card_version_symbols(card_version_id=version.id, symbol_ids=symbol_ids or [])
        _save_parse_result(version, raw_ocr, normalized_fields, confidence)
        _save_parsed_snapshot(
            version,
            normalized_fields=normalized_fields,
            keyword_ids=keyword_ids or [],
            tag_ids=tag_ids or [],
            type_ids=type_ids or [],
            symbol_ids=symbol_ids or [],
        )
        _save_image_record(version, item.source_file, checksum)
        _mark_item_completed(item)

        card.label = parsed_name
        card.latest_version = version
        card.updated_at = now_utc()
        card.save(update_fields=["label", "latest_version", "updated_at"])
        return version


def list_cards(
    *,
    query: str | None,
    max_confidence: float | None,
    keyword_ids: list[str] | None = None,
    tag_ids: list[str] | None = None,
    symbol_ids: list[str] | None = None,
    type_ids: list[str] | None = None,
    mana_cost: str | None = None,
    template_id: str | None = None,
    attack_min: int | None = None,
    attack_max: int | None = None,
    health_min: int | None = None,
    health_max: int | None = None,
    page: int = 1,
    page_size: int = 72,
) -> PaginatedCardList:
    normalized_page = max(page, 1)
    normalized_page_size = max(1, min(page_size, 100))
    versions = (
        CardVersion.objects.filter(is_latest=True)
        .select_related("card", "template", "previous_version")
        .prefetch_related(
            "images",
            Prefetch(
                "card_version_keywords",
                queryset=CardVersionKeyword.objects.select_related("keyword").order_by("keyword__label"),
            ),
            Prefetch(
                "card_version_tags",
                queryset=CardVersionTag.objects.select_related("tag").order_by("tag__label"),
            ),
            Prefetch(
                "card_version_symbols",
                queryset=CardVersionSymbol.objects.select_related("symbol").order_by("symbol__label"),
            ),
            Prefetch(
                "card_version_types",
                queryset=CardVersionType.objects.select_related("type").order_by("type__label"),
            ),
        )
        .order_by("-updated_at")
    )
    versions = apply_card_search(versions, query)
    versions = _apply_card_filters(
        versions,
        max_confidence=max_confidence,
        mana_cost=mana_cost,
        template_id=template_id,
        attack_min=attack_min,
        attack_max=attack_max,
        health_min=health_min,
        health_max=health_max,
    )
    versions = _filter_by_links(versions, CardVersionKeyword, "keyword_id", keyword_ids)
    versions = _filter_by_links(versions, CardVersionTag, "tag_id", tag_ids)
    versions = _filter_by_links(versions, CardVersionSymbol, "symbol_id", symbol_ids)
    versions = _filter_by_links(versions, CardVersionType, "type_id", type_ids)

    total_count = versions.count()
    offset = (normalized_page - 1) * normalized_page_size
    version_rows = list(versions[offset : offset + normalized_page_size])
    if not version_rows:
        return PaginatedCardList(
            count=total_count,
            page=normalized_page,
            page_size=normalized_page_size,
            results=[],
        )

    results: list[CardListRow] = []
    for version in version_rows:
        results.append(
            CardListRow(
                version=version,
                image=next(iter(version.images.all()), None),
                keywords=[row.keyword for row in version.card_version_keywords.all()],
                tags=[row.tag for row in version.card_version_tags.all()],
                symbols=[row.symbol for row in version.card_version_symbols.all()],
                types=[row.type for row in version.card_version_types.all()],
            )
        )

    return PaginatedCardList(
        count=total_count,
        page=normalized_page,
        page_size=normalized_page_size,
        results=results,
    )


def get_card(card_id: str) -> Card | None:
    return Card.objects.filter(id=card_id).first()


def get_latest_card_version(card_id: str) -> CardVersion | None:
    return (
        CardVersion.objects.filter(card_id=card_id, is_latest=True).select_related("card", "template", "previous_version")
        .order_by("-version_number")
        .first()
    )


def get_card_image(card_version_id: str) -> CardVersionImage | None:
    images = CardVersionImage.objects.filter(card_version_id=card_version_id).order_by("-created_at")
    first_image: CardVersionImage | None = None
    for image in images:
        if first_image is None:
            first_image = image
        if resolve_image_file_path(image) is not None:
            return image
    return first_image


def list_latest_card_version_reparse_sources() -> list[LatestCardVersionReparseSource]:
    versions = [
        card.latest_version
        for card in Card.objects.exclude(latest_version__isnull=True)
        .select_related("latest_version__template")
        .prefetch_related("latest_version__images")
        .order_by("id")
        if card.latest_version is not None
    ]
    if not versions:
        return []

    out: list[LatestCardVersionReparseSource] = []
    for version in versions:
        image = next(iter(version.images.all()), None)
        if image is None:
            continue
        image_path = _resolve_reparse_image_path(image)
        if image_path is None:
            continue
        out.append(
            LatestCardVersionReparseSource(
                card_version_id=version.id,
                template_id=version.template_id,
                image_path=image_path,
            )
        )
    return out


def list_card_generations(card_id: str) -> list[CardVersion]:
    return list(
        CardVersion.objects.filter(card_id=card_id)
        .select_related("card", "template", "previous_version")
        .order_by("-version_number")
    )


def get_parse_result(parse_result_id: str | None) -> ParseResult | None:
    if not parse_result_id:
        return None
    return ParseResult.objects.filter(id=parse_result_id).first()


def update_card(
    *,
    card_id: str,
    name: str | None,
    type_line: str | None,
    mana_cost: str | None,
    rules_text: str | None,
) -> tuple[Card, CardVersion] | None:
    card = get_card(card_id)
    version = get_latest_card_version(card_id)
    if card is None or version is None:
        return None

    if name is not None:
        card.label = name
        card.key = normalize_slug_key(name)
        version.name = name
    if type_line is not None:
        version.type_line = type_line
    if mana_cost is not None:
        version.mana_cost = mana_cost
    if rules_text is not None:
        version.rules_text = rules_text

    card.updated_at = now_utc()
    version.updated_at = now_utc()
    card.save()
    version.save()
    return card, version


def decode_field_sources(raw: str) -> FieldSourcesPayload:
    default: FieldSourcesPayload = {
        "fields": dict(DEFAULT_FIELD_SOURCES["fields"]),
        "metadata": dict(DEFAULT_FIELD_SOURCES["metadata"]),
    }
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return default
    if not isinstance(payload, dict):
        return default

    fields = payload.get("fields")
    metadata = payload.get("metadata")
    if isinstance(fields, dict):
        for field_name in SCALAR_FIELD_NAMES:
            value = fields.get(field_name)
            if value in {FIELD_SOURCE_AUTO, FIELD_SOURCE_MANUAL}:
                default["fields"][field_name] = value
    if isinstance(metadata, dict):
        for group_name in METADATA_GROUP_NAMES:
            value = metadata.get(group_name)
            if value in {FIELD_SOURCE_AUTO, FIELD_SOURCE_MANUAL}:
                default["metadata"][group_name] = value
    return default


def decode_parsed_snapshot(raw: str) -> ParsedSnapshotPayload:
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
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return default
    if not isinstance(payload, dict):
        return default

    fields = payload.get("fields")
    metadata = payload.get("metadata")
    if isinstance(fields, dict):
        for field_name in SCALAR_FIELD_NAMES:
            if field_name in fields:
                default["fields"][field_name] = fields[field_name]
    if isinstance(metadata, dict):
        mapping = {
            "keyword_ids": "keyword_ids",
            "tag_ids": "tag_ids",
            "type_ids": "type_ids",
            "symbol_ids": "symbol_ids",
        }
        for key in mapping.values():
            value = metadata.get(key)
            if isinstance(value, list):
                default["metadata"][key] = [str(item) for item in value]
    return default


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
            _apply_scalar_value(version, field_name, snapshot["fields"].get(field_name))
            field_sources["fields"][field_name] = FIELD_SOURCE_AUTO
            if field_name == "name":
                restored_name = True
        for group_name in restore_metadata_groups:
            if group_name not in field_sources["metadata"]:
                continue
            _restore_metadata_group_from_snapshot(version.id, group_name, snapshot)
            field_sources["metadata"][group_name] = FIELD_SOURCE_AUTO

        for field_name in SCALAR_FIELD_NAMES:
            if field_name not in updates:
                continue
            _apply_scalar_value(version, field_name, updates[field_name])
            field_sources["fields"][field_name] = FIELD_SOURCE_MANUAL
            if field_name == "name":
                restored_name = True

        if "keyword_ids" in updates:
            replace_card_version_keywords(
                card_version_id=version.id,
                keyword_ids=_string_list(updates.get("keyword_ids")),
            )
            field_sources["metadata"]["keywords"] = FIELD_SOURCE_MANUAL
        if "tag_ids" in updates:
            replace_card_version_tags(
                card_version_id=version.id,
                tag_ids=_string_list(updates.get("tag_ids")),
            )
            field_sources["metadata"]["tags"] = FIELD_SOURCE_MANUAL
        if "type_ids" in updates:
            replace_card_version_types(
                card_version_id=version.id,
                type_ids=_string_list(updates.get("type_ids")),
            )
            field_sources["metadata"]["types"] = FIELD_SOURCE_MANUAL
        if "symbol_ids" in updates:
            replace_card_version_symbols(
                card_version_id=version.id,
                symbol_ids=_string_list(updates.get("symbol_ids")),
            )
            field_sources["metadata"]["symbols"] = FIELD_SOURCE_MANUAL

        if restored_name or "name" in updates:
            card.label = version.name
            card.key = normalize_slug_key(version.name)
            card.updated_at = now_utc()
            card.save(update_fields=["label", "key", "updated_at"])

        version.mana_symbols_json = json.dumps(extract_mana_symbols({"mana_cost": version.mana_cost}))
        version.field_sources_json = json.dumps(field_sources)
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
    version.mana_symbols_json = json.dumps(extract_mana_symbols(normalized_fields))
    version.attack = to_int_or_none(normalized_fields.get("attack"))
    version.health = to_int_or_none(normalized_fields.get("health"))
    version.rules_text = normalized_fields.get("rules_text", "")
    version.confidence = float(confidence.get("overall", 0.0))


def upsert_card_search(*, card_id: str, version: CardVersion) -> None:
    return None


def _update_existing_version(
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
    _apply_parsed_output_to_version(
        version,
        normalized_fields=normalized_fields,
        confidence=confidence,
        keyword_ids=keyword_ids,
        tag_ids=tag_ids,
        type_ids=type_ids,
        symbol_ids=symbol_ids,
    )
    _save_parse_result(version, raw_ocr, normalized_fields, confidence)
    _save_parsed_snapshot(
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
        card = Card.objects.filter(id=version.card_id).first()
        if card is not None:
            card.label = version.name
            card.key = normalize_slug_key(version.name)
            card.updated_at = now_utc()
            card.save(update_fields=["label", "key", "updated_at"])
    _mark_item_completed(item)
    return version


def _create_new_version(
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
        mana_symbols_json=json.dumps(extract_mana_symbols(normalized_fields)),
        attack=to_int_or_none(normalized_fields.get("attack")),
        health=to_int_or_none(normalized_fields.get("health")),
        rules_text=normalized_fields.get("rules_text", ""),
        confidence=float(confidence.get("overall", 0.0)),
        field_sources_json=json.dumps(DEFAULT_FIELD_SOURCES),
        parsed_snapshot_json=json.dumps(_build_parsed_snapshot(normalized_fields, [], [], [], [])),
        is_latest=True,
        previous_version_id=previous_version_id,
    )


def _save_parse_result(
    version: CardVersion,
    raw_ocr: dict[str, object],
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
) -> None:
    parse_result = ParseResult.objects.create(
        card_version=version,
        raw_ocr_json=json.dumps(raw_ocr),
        normalized_fields_json=json.dumps(normalized_fields),
        confidence_json=json.dumps(confidence),
    )
    version.parse_result_id = parse_result.id
    version.save(update_fields=["parse_result_id"])


def _save_parsed_snapshot(
    version: CardVersion,
    *,
    normalized_fields: dict[str, str],
    keyword_ids: list[str],
    tag_ids: list[str],
    type_ids: list[str],
    symbol_ids: list[str],
) -> None:
    version.parsed_snapshot_json = json.dumps(
        _build_parsed_snapshot(
            normalized_fields,
            keyword_ids,
            tag_ids,
            type_ids,
            symbol_ids,
        )
    )
    version.save(update_fields=["parsed_snapshot_json"])


def _save_image_record(version: CardVersion, source_file: str, checksum: str) -> None:
    resolved_source_file = resolve_storage_path(source_file)
    stored_path = store_image(resolved_source_file, checksum)
    CardVersionImage.objects.create(
        card_version=version,
        source_file=relativize_storage_path(source_file, default_root="uploads"),
        stored_path=stored_path,
        checksum=checksum,
        updated_at=now_utc(),
    )


def _mark_item_completed(item: ImportJobItem) -> None:
    item.status = ImportJobStatus.completed
    item.error_message = None
    item.updated_at = now_utc()
    item.save(update_fields=["status", "error_message", "updated_at"])


def _apply_card_filters(queryset: QuerySet[CardVersion], **filters: object) -> QuerySet[CardVersion]:
    if filters["max_confidence"] is not None:
        queryset = queryset.filter(confidence__lte=filters["max_confidence"])
    if filters["mana_cost"]:
        queryset = queryset.filter(mana_cost=filters["mana_cost"])
    if filters["template_id"]:
        queryset = queryset.filter(template_id=filters["template_id"])
    if filters["attack_min"] is not None:
        queryset = queryset.filter(attack__isnull=False, attack__gte=filters["attack_min"])
    if filters["attack_max"] is not None:
        queryset = queryset.filter(attack__isnull=False, attack__lte=filters["attack_max"])
    if filters["health_min"] is not None:
        queryset = queryset.filter(health__isnull=False, health__gte=filters["health_min"])
    if filters["health_max"] is not None:
        queryset = queryset.filter(health__isnull=False, health__lte=filters["health_max"])
    return queryset


def _filter_by_links(
    queryset: QuerySet[CardVersion],
    link_model: type[CardVersionKeyword] | type[CardVersionTag] | type[CardVersionSymbol] | type[CardVersionType],
    link_field: str,
    values: list[str] | None,
) -> QuerySet[CardVersion]:
    if not values:
        return queryset
    version_ids = link_model.objects.filter(**{f"{link_field}__in": values}).values_list(
        "card_version_id",
        flat=True,
    )
    return queryset.filter(id__in=version_ids)


def _resolve_reparse_image_path(image: CardVersionImage) -> Path | None:
    return resolve_image_file_path(image)


def resolve_image_file_path(image: CardVersionImage) -> Path | None:
    stored_path = resolve_storage_path(image.stored_path)
    if stored_path.exists():
        return stored_path

    source_path = resolve_storage_path(image.source_file)
    if source_path.exists():
        return source_path

    return None


def _apply_parsed_output_to_version(
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
        version.mana_symbols_json = json.dumps(extract_mana_symbols(normalized_fields))
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


def _build_parsed_snapshot(
    normalized_fields: dict[str, str],
    keyword_ids: list[str],
    tag_ids: list[str],
    type_ids: list[str],
    symbol_ids: list[str],
) -> dict[str, object]:
    return {
        "fields": {
            "name": normalized_fields.get("name", ""),
            "type_line": normalized_fields.get("type_line", ""),
            "mana_cost": normalized_fields.get("mana_cost", ""),
            "attack": to_int_or_none(normalized_fields.get("attack")),
            "health": to_int_or_none(normalized_fields.get("health")),
            "rules_text": normalized_fields.get("rules_text", ""),
        },
        "metadata": {
            "keyword_ids": keyword_ids,
            "tag_ids": tag_ids,
            "type_ids": type_ids,
            "symbol_ids": symbol_ids,
        },
    }


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _apply_scalar_value(version: CardVersion, field_name: str, value: object) -> None:
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
        version.attack = _coerce_optional_int(value)
        return
    if field_name == "health":
        version.health = _coerce_optional_int(value)


def _coerce_optional_int(value: object) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _restore_metadata_group_from_snapshot(
    card_version_id: str,
    group_name: str,
    snapshot: ParsedSnapshotPayload,
) -> None:
    metadata = snapshot.get("metadata", {})
    if group_name == "keywords":
        replace_card_version_keywords(
            card_version_id=card_version_id,
            keyword_ids=_string_list(metadata.get("keyword_ids")),
        )
    elif group_name == "tags":
        replace_card_version_tags(
            card_version_id=card_version_id,
            tag_ids=_string_list(metadata.get("tag_ids")),
        )
    elif group_name == "types":
        replace_card_version_types(
            card_version_id=card_version_id,
            type_ids=_string_list(metadata.get("type_ids")),
        )
    elif group_name == "symbols":
        replace_card_version_symbols(
            card_version_id=card_version_id,
            symbol_ids=_string_list(metadata.get("symbol_ids")),
        )
