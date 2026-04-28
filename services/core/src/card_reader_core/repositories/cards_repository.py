from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from django.db import transaction
from django.db.models import QuerySet

from ..storage import store_image
from .helpers import extract_mana_symbols, normalize_slug_key, to_int_or_none
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
    now_utc,
)
from card_reader_core.search.cards import apply_card_search


@dataclass(frozen=True)
class LatestCardVersionReparseSource:
    card_version_id: str
    template_id: str
    image_path: Path


def save_parsed_card(
    *,
    item: ImportJobItem,
    template_id: str,
    checksum: str,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
    raw_ocr: dict[str, object],
    reparse_existing: bool = True,
) -> CardVersion:
    parsed_name = normalized_fields.get("name", "").strip() or Path(item.source_file).stem
    card_key = normalize_slug_key(parsed_name)

    with transaction.atomic():
        card = Card.objects.filter(key=card_key).first()
        if card is None:
            card = Card.objects.create(key=card_key, label=parsed_name)

        latest = get_latest_card_version(card.id)
        if latest and latest.image_hash == checksum and reparse_existing:
            return _update_existing_version(item, latest, normalized_fields, confidence, raw_ocr)

        version = _create_new_version(item, card, template_id, checksum, normalized_fields, confidence)
        _save_parse_result(version, raw_ocr, normalized_fields, confidence)
        _save_image_record(version, item.source_file, checksum)
        _mark_item_completed(item)

        card.label = parsed_name
        card.latest_version_id = version.id
        card.updated_at = now_utc()
        card.save(update_fields=["label", "latest_version_id", "updated_at"])
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
) -> list[tuple[Card, CardVersion]]:
    versions = CardVersion.objects.filter(is_latest=True).order_by("-updated_at")
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

    version_rows = list(versions)
    cards = Card.objects.filter(id__in=[version.card_id for version in version_rows])
    cards_by_id = {card.id: card for card in cards}
    return [(cards_by_id[version.card_id], version) for version in version_rows]


def get_card(card_id: str) -> Card | None:
    return Card.objects.filter(id=card_id).first()


def get_latest_card_version(card_id: str) -> CardVersion | None:
    return (
        CardVersion.objects.filter(card_id=card_id, is_latest=True)
        .order_by("-version_number")
        .first()
    )


def get_card_image(card_version_id: str) -> CardVersionImage | None:
    return CardVersionImage.objects.filter(card_version_id=card_version_id).first()


def list_latest_card_version_reparse_sources() -> list[LatestCardVersionReparseSource]:
    latest_version_ids = list(
        Card.objects.exclude(latest_version_id__isnull=True)
        .exclude(latest_version_id="")
        .values_list("latest_version_id", flat=True)
    )
    if not latest_version_ids:
        return []

    versions = list(
        CardVersion.objects.filter(id__in=latest_version_ids)
        .only("id", "template_id")
        .order_by("id")
    )
    if not versions:
        return []

    images_by_version_id = {
        row.card_version_id: row
        for row in CardVersionImage.objects.filter(
            card_version_id__in=[version.id for version in versions]
        ).only("card_version_id", "source_file", "stored_path")
    }

    out: list[LatestCardVersionReparseSource] = []
    for version in versions:
        image = images_by_version_id.get(version.id)
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
    return list(CardVersion.objects.filter(card_id=card_id).order_by("-version_number"))


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
) -> CardVersion:
    apply_parsed_fields_to_version(version, normalized_fields=normalized_fields, confidence=confidence)
    _save_parse_result(version, raw_ocr, normalized_fields, confidence)
    version.updated_at = now_utc()
    version.save()
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
        card_id=card.id,
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
        card_version_id=version.id,
        raw_ocr_json=json.dumps(raw_ocr),
        normalized_fields_json=json.dumps(normalized_fields),
        confidence_json=json.dumps(confidence),
    )
    version.parse_result_id = parse_result.id
    version.save(update_fields=["parse_result_id"])


def _save_image_record(version: CardVersion, source_file: str, checksum: str) -> None:
    stored_path = store_image(Path(source_file), checksum)
    CardVersionImage.objects.create(
        card_version_id=version.id,
        source_file=source_file,
        stored_path=str(stored_path),
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
    stored_path = Path(image.stored_path)
    if stored_path.exists():
        return stored_path

    source_path = Path(image.source_file)
    if source_path.exists():
        return source_path

    return None
