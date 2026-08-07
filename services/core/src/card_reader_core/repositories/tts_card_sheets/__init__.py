from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import hashlib
import json
from pathlib import Path
from collections.abc import Iterator

from django.db import transaction
from django.db.models import F, Max, Prefetch, Q, QuerySet
from PIL import Image

from card_reader_core.models import (
    TTS_CARD_SHEET_CAPACITY,
    TTS_CARD_SHEET_LAYOUT_VERSION,
    Card,
    CardVersion,
    CardVersionImage,
    TtsCardSheet,
    TtsCardSheetSlot,
    now_utc,
)
from card_reader_core.repositories.cards import resolve_image_file_path

_RENDER_DEBOUNCE = timedelta(seconds=2)
_RENDER_MAX_DEBOUNCE = timedelta(seconds=30)
_RENDER_CLAIM_TIMEOUT = timedelta(minutes=10)
_RENDERER_FINGERPRINT_VERSION = 1


@dataclass(frozen=True)
class TtsCardImageSource:
    card: Card
    version: CardVersion
    image: CardVersionImage
    path: Path


@dataclass(frozen=True)
class TtsCardSheetAssignment:
    card_id: str
    sheet_id: str
    sheet_sequence: int
    layout_version: int
    slot_index: int
    desired_revision: int
    rendered_revision: int
    rendered_checksum: str
    image_checksum: str


def list_usable_card_sources(card_ids: list[str] | None = None) -> list[TtsCardImageSource]:
    cards = _card_source_queryset(card_ids)
    return _usable_sources_from_cards(list(cards))


def iter_usable_card_source_batches(
    *, batch_size: int = 500
) -> Iterator[list[TtsCardImageSource]]:
    normalized_batch_size = max(1, batch_size)
    cards = _card_source_queryset(None)
    offset = 0
    while True:
        page = list(cards[offset : offset + normalized_batch_size])
        if not page:
            break
        yield _usable_sources_from_cards(page)
        offset += len(page)


def _card_source_queryset(card_ids: list[str] | None) -> QuerySet[Card]:
    cards = Card.objects.filter(latest_version__isnull=False).select_related("latest_version")
    if card_ids is not None:
        cards = cards.filter(id__in=card_ids)
    return cards.prefetch_related(
        Prefetch(
            "latest_version__images",
            queryset=CardVersionImage.objects.order_by("-created_at", "-id"),
        )
    ).order_by("created_at", "id")


def _usable_sources_from_cards(cards: list[Card]) -> list[TtsCardImageSource]:
    sources: list[TtsCardImageSource] = []
    for card in cards:
        version = card.latest_version
        if version is None:
            continue
        for image in version.images.all():
            path = resolve_tts_card_image_path(image)
            if path is None:
                continue
            sources.append(TtsCardImageSource(card=card, version=version, image=image, path=path))
            break
    return sources


def resolve_tts_card_image_path(image: CardVersionImage) -> Path | None:
    path = resolve_image_file_path(image)
    if path is None:
        return None
    try:
        with Image.open(path) as source_image:
            source_image.verify()
    except (OSError, SyntaxError, ValueError):
        return None
    return path


@transaction.atomic
def sync_card_sources(sources: list[TtsCardImageSource]) -> set[str]:
    affected_sheet_ids: set[str] = set()
    for source in sources:
        canonical = TtsCardSheetSlot.objects.filter(card_identity_id=source.card.id).first()
        if canonical is None:
            canonical = _allocate_slot(source)
        affected_sheet_ids.add(str(canonical.sheet_id))

        slots = list(
            TtsCardSheetSlot.objects.select_for_update().filter(resolved_card_id=source.card.id)
        )
        if canonical.id not in {slot.id for slot in slots}:
            slots.append(canonical)
        for slot in slots:
            changed = (
                slot.resolved_card_id != source.card.id
                or slot.card_version_id != source.version.id
                or slot.image_id != source.image.id
                or slot.image_checksum != source.image.checksum
                or slot.image_stored_path != source.image.stored_path
            )
            if not changed:
                continue
            slot.resolved_card = source.card
            slot.card_version = source.version
            slot.image = source.image
            slot.image_checksum = source.image.checksum
            slot.image_stored_path = source.image.stored_path
            slot.updated_at = now_utc()
            slot.save(
                update_fields=[
                    "resolved_card",
                    "card_version",
                    "image",
                    "image_checksum",
                    "image_stored_path",
                    "updated_at",
                ]
            )
            affected_sheet_ids.add(str(slot.sheet_id))

    _refresh_sheet_fingerprints(affected_sheet_ids)
    return affected_sheet_ids


@transaction.atomic
def sync_merged_card_source(
    *, source_card_ids: list[str], target_source: TtsCardImageSource
) -> set[str]:
    normalized_source_ids = list(dict.fromkeys(source_card_ids))
    slots = list(
        TtsCardSheetSlot.objects.select_for_update().filter(
            resolved_card_id__in=normalized_source_ids
        )
    )
    affected_sheet_ids = {str(slot.sheet_id) for slot in slots}
    for slot in slots:
        slot.resolved_card = target_source.card
        slot.card_version = target_source.version
        slot.image = target_source.image
        slot.image_checksum = target_source.image.checksum
        slot.image_stored_path = target_source.image.stored_path
        slot.updated_at = now_utc()
        slot.save(
            update_fields=[
                "resolved_card",
                "card_version",
                "image",
                "image_checksum",
                "image_stored_path",
                "updated_at",
            ]
        )
    affected_sheet_ids.update(sync_card_sources([target_source]))
    _refresh_sheet_fingerprints(affected_sheet_ids)
    return affected_sheet_ids


def get_card_sheet_assignments(card_ids: list[str]) -> dict[str, TtsCardSheetAssignment]:
    slots = TtsCardSheetSlot.objects.filter(card_identity_id__in=card_ids).select_related("sheet")
    return {
        slot.card_identity_id: TtsCardSheetAssignment(
            card_id=slot.card_identity_id,
            sheet_id=str(slot.sheet_id),
            sheet_sequence=slot.sheet.sequence,
            layout_version=slot.sheet.layout_version,
            slot_index=slot.slot_index,
            desired_revision=slot.sheet.desired_revision,
            rendered_revision=slot.sheet.rendered_revision,
            rendered_checksum=slot.sheet.rendered_checksum,
            image_checksum=slot.image_checksum,
        )
        for slot in slots
    }


def prioritize_sheets(sheet_ids: list[str]) -> None:
    if not sheet_ids:
        return
    now = now_utc()
    TtsCardSheet.objects.filter(id__in=sheet_ids).update(
        render_priority=1,
        render_not_before=now,
        updated_at=now,
    )


def request_sheet_rerender(sheet_ids: list[str]) -> None:
    if not sheet_ids:
        return
    now = now_utc()
    TtsCardSheet.objects.filter(
        id__in=sheet_ids,
        desired_revision=F("rendered_revision"),
    ).update(
        desired_revision=F("desired_revision") + 1,
        dirty_since=now,
        render_not_before=now,
        render_priority=1,
        updated_at=now,
    )
    prioritize_sheets(sheet_ids)


@transaction.atomic
def claim_next_renderable_sheet() -> TtsCardSheet | None:
    now = now_utc()
    stale_before = now - _RENDER_CLAIM_TIMEOUT
    sheet = (
        TtsCardSheet.objects.select_for_update()
        .filter(desired_revision__gt=F("rendered_revision"))
        .filter(Q(render_not_before__isnull=True) | Q(render_not_before__lte=now))
        .filter(Q(render_claimed_at__isnull=True) | Q(render_claimed_at__lt=stale_before))
        .order_by("-render_priority", "render_not_before", "sequence")
        .first()
    )
    if sheet is None:
        return None
    sheet.render_claimed_at = now
    sheet.updated_at = now
    sheet.save(update_fields=["render_claimed_at", "updated_at"])
    return sheet


@transaction.atomic
def claim_sheet_for_render(sheet_id: str) -> TtsCardSheet | None:
    sheet = TtsCardSheet.objects.select_for_update().filter(id=sheet_id).first()
    if sheet is None or sheet.desired_revision <= sheet.rendered_revision:
        return None
    now = now_utc()
    stale_before = now - _RENDER_CLAIM_TIMEOUT
    if sheet.render_claimed_at is not None and sheet.render_claimed_at >= stale_before:
        return None
    sheet.render_claimed_at = now
    sheet.updated_at = now
    sheet.save(update_fields=["render_claimed_at", "updated_at"])
    return sheet


def get_sheet_with_slots(sheet_id: str) -> TtsCardSheet | None:
    return (
        TtsCardSheet.objects.filter(id=sheet_id)
        .prefetch_related("slots")
        .first()
    )


def list_sheet_ids_needing_render(sheet_ids: list[str]) -> list[str]:
    return list(
        TtsCardSheet.objects.filter(id__in=sheet_ids, desired_revision__gt=F("rendered_revision"))
        .order_by("sequence")
        .values_list("id", flat=True)
    )


@transaction.atomic
def mark_render_succeeded(
    *,
    sheet_id: str,
    rendered_revision: int,
    rendered_fingerprint: str,
    rendered_checksum: str,
) -> TtsCardSheet:
    sheet = TtsCardSheet.objects.select_for_update().get(id=sheet_id)
    now = now_utc()
    published_at = now.replace(microsecond=0)
    if sheet.published_at is not None and published_at <= sheet.published_at:
        published_at = sheet.published_at + timedelta(seconds=1)
    sheet.rendered_revision = rendered_revision
    sheet.rendered_fingerprint = rendered_fingerprint
    sheet.rendered_checksum = rendered_checksum
    sheet.published_at = published_at
    sheet.render_claimed_at = None
    sheet.render_failure_count = 0
    sheet.last_render_error = ""
    if sheet.desired_revision == rendered_revision:
        sheet.dirty_since = None
        sheet.render_not_before = None
        sheet.render_priority = 0
    else:
        sheet.render_not_before = now
    sheet.updated_at = now
    sheet.save()
    return sheet


@transaction.atomic
def mark_render_failed(*, sheet_id: str, error: str) -> None:
    sheet = TtsCardSheet.objects.select_for_update().get(id=sheet_id)
    failure_count = sheet.render_failure_count + 1
    delay_seconds = min(300, 2 ** min(failure_count, 8))
    now = now_utc()
    sheet.render_claimed_at = None
    sheet.render_failure_count = failure_count
    sheet.last_render_error = error[:2000]
    sheet.render_not_before = now + timedelta(seconds=delay_seconds)
    sheet.updated_at = now
    sheet.save(
        update_fields=[
            "render_claimed_at",
            "render_failure_count",
            "last_render_error",
            "render_not_before",
            "updated_at",
        ]
    )


def _allocate_slot(source: TtsCardImageSource) -> TtsCardSheetSlot:
    sheet = (
        TtsCardSheet.objects.select_for_update()
        .filter(
            layout_version=TTS_CARD_SHEET_LAYOUT_VERSION,
            next_slot_index__lt=TTS_CARD_SHEET_CAPACITY,
        )
        .order_by("-sequence")
        .first()
    )
    if sheet is None:
        max_sequence = TtsCardSheet.objects.aggregate(value=Max("sequence"))["value"] or 0
        sheet = TtsCardSheet.objects.create(
            sequence=max_sequence + 1,
            layout_version=TTS_CARD_SHEET_LAYOUT_VERSION,
        )
    slot_index = sheet.next_slot_index
    sheet.next_slot_index += 1
    sheet.updated_at = now_utc()
    sheet.save(update_fields=["next_slot_index", "updated_at"])
    return TtsCardSheetSlot.objects.create(
        sheet=sheet,
        slot_index=slot_index,
        card_identity_id=source.card.id,
        resolved_card=source.card,
        card_version=source.version,
        image=source.image,
        image_checksum=source.image.checksum,
        image_stored_path=source.image.stored_path,
    )


def _refresh_sheet_fingerprints(sheet_ids: set[str]) -> None:
    now = now_utc()
    for sheet in TtsCardSheet.objects.select_for_update().filter(id__in=sheet_ids):
        slots = list(
            TtsCardSheetSlot.objects.filter(sheet=sheet)
            .order_by("slot_index")
            .values_list("slot_index", "image_checksum")
        )
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "renderer": _RENDERER_FINGERPRINT_VERSION,
                    "layout": sheet.layout_version,
                    "slots": slots,
                },
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        if fingerprint == sheet.desired_fingerprint:
            continue
        dirty_since = sheet.dirty_since or now
        render_not_before = min(now + _RENDER_DEBOUNCE, dirty_since + _RENDER_MAX_DEBOUNCE)
        sheet.desired_revision += 1
        sheet.desired_fingerprint = fingerprint
        sheet.dirty_since = dirty_since
        sheet.render_not_before = render_not_before
        sheet.updated_at = now
        sheet.save(
            update_fields=[
                "desired_revision",
                "desired_fingerprint",
                "dirty_since",
                "render_not_before",
                "updated_at",
            ]
        )


__all__ = [
    "TtsCardImageSource",
    "TtsCardSheetAssignment",
    "claim_next_renderable_sheet",
    "claim_sheet_for_render",
    "get_card_sheet_assignments",
    "get_sheet_with_slots",
    "iter_usable_card_source_batches",
    "list_sheet_ids_needing_render",
    "list_usable_card_sources",
    "mark_render_failed",
    "mark_render_succeeded",
    "prioritize_sheets",
    "request_sheet_rerender",
    "resolve_tts_card_image_path",
    "sync_card_sources",
    "sync_merged_card_source",
]
