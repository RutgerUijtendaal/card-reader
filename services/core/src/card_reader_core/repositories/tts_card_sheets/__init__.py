from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import time
from collections.abc import Callable, Iterator
from typing import TypeVar

from django.db import IntegrityError, OperationalError, connection, transaction
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
from card_reader_core.storage import relativize_storage_path

_RENDER_DEBOUNCE = timedelta(seconds=2)
_RENDER_MAX_DEBOUNCE = timedelta(seconds=30)
_RENDER_CLAIM_TIMEOUT = timedelta(minutes=10)
_RENDERER_FINGERPRINT_VERSION = 1
_SQLITE_WRITE_RETRY_ATTEMPTS = 6
_SLOT_RESERVATION_ATTEMPTS = 16
_CLAIM_RESERVATION_ATTEMPTS = 16

_RetryResult = TypeVar("_RetryResult")


class TtsCardSheetAllocationError(RuntimeError):
    pass


class _SlotReservationLost(RuntimeError):
    pass


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


def sync_card_sources(sources: list[TtsCardImageSource]) -> set[str]:
    return _retry_sqlite_write(lambda: _sync_card_sources_once(sources))


def _retry_sqlite_write(operation: Callable[[], _RetryResult]) -> _RetryResult:
    for attempt in range(_SQLITE_WRITE_RETRY_ATTEMPTS):
        try:
            return operation()
        except OperationalError as exc:
            is_locked = connection.vendor == "sqlite" and "locked" in str(exc).lower()
            if not is_locked or attempt == _SQLITE_WRITE_RETRY_ATTEMPTS - 1:
                raise
            time.sleep(0.05 * (2**attempt))
    raise TtsCardSheetAllocationError("TTS card-sheet write retries were exhausted.")


@transaction.atomic
def _sync_card_sources_once(sources: list[TtsCardImageSource]) -> set[str]:
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
                or slot.image_stored_path != _source_snapshot_path(source)
            )
            if not changed:
                continue
            slot.resolved_card = source.card
            slot.card_version = source.version
            slot.image = source.image
            slot.image_checksum = source.image.checksum
            slot.image_stored_path = _source_snapshot_path(source)
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
    *,
    source_card_ids: list[str],
    target_card_id: str,
    target_source: TtsCardImageSource | None,
) -> set[str]:
    normalized_source_ids = list(dict.fromkeys(source_card_ids))
    target_card = Card.objects.select_for_update().get(id=target_card_id)
    slots = list(
        TtsCardSheetSlot.objects.select_for_update().filter(
            resolved_card_id__in=normalized_source_ids
        )
    )
    affected_sheet_ids = {str(slot.sheet_id) for slot in slots}
    for slot in slots:
        slot.resolved_card = target_card
        update_fields = ["resolved_card", "updated_at"]
        if target_source is not None:
            slot.card_version = target_source.version
            slot.image = target_source.image
            slot.image_checksum = target_source.image.checksum
            slot.image_stored_path = _source_snapshot_path(target_source)
            update_fields.extend(
                [
                    "card_version",
                    "image",
                    "image_checksum",
                    "image_stored_path",
                ]
            )
        slot.updated_at = now_utc()
        slot.save(update_fields=update_fields)
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
    sheets = TtsCardSheet.objects.filter(id__in=sheet_ids)
    sheets.update(
        render_priority=1,
        updated_at=now,
    )
    sheets.filter(
        Q(render_failure_count=0)
        | Q(render_not_before__isnull=True)
        | Q(render_not_before__lte=now)
    ).update(render_not_before=now, updated_at=now)


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


def ensure_sheet_render_requested(sheet_ids: list[str]) -> None:
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
    TtsCardSheet.objects.filter(id__in=sheet_ids).update(
        render_priority=1,
        updated_at=now,
    )


def claim_next_renderable_sheet() -> TtsCardSheet | None:
    return _retry_sqlite_write(_claim_next_renderable_sheet_once)


def _claim_next_renderable_sheet_once() -> TtsCardSheet | None:
    for _attempt in range(_CLAIM_RESERVATION_ATTEMPTS):
        now = now_utc()
        stale_before = now - _RENDER_CLAIM_TIMEOUT
        claimable = (
            TtsCardSheet.objects.filter(desired_revision__gt=F("rendered_revision"))
            .filter(Q(render_not_before__isnull=True) | Q(render_not_before__lte=now))
            .filter(Q(render_claimed_at__isnull=True) | Q(render_claimed_at__lt=stale_before))
        )
        sheet_id = (
            claimable.order_by("-render_priority", "render_not_before", "sequence")
            .values_list("id", flat=True)
            .first()
        )
        if sheet_id is None:
            return None
        claimed = claimable.filter(id=sheet_id).update(render_claimed_at=now, updated_at=now)
        if claimed == 1:
            return TtsCardSheet.objects.filter(id=sheet_id, render_claimed_at=now).first()
    return None


def claim_sheet_for_render(
    sheet_id: str,
    *,
    respect_not_before: bool = False,
) -> TtsCardSheet | None:
    return _retry_sqlite_write(
        lambda: _claim_sheet_for_render_once(
            sheet_id,
            respect_not_before=respect_not_before,
        )
    )


def _claim_sheet_for_render_once(
    sheet_id: str,
    *,
    respect_not_before: bool,
) -> TtsCardSheet | None:
    now = now_utc()
    stale_before = now - _RENDER_CLAIM_TIMEOUT
    claimable = (
        TtsCardSheet.objects.filter(id=sheet_id, desired_revision__gt=F("rendered_revision"))
        .filter(Q(render_claimed_at__isnull=True) | Q(render_claimed_at__lt=stale_before))
    )
    if respect_not_before:
        claimable = claimable.filter(
            Q(render_not_before__isnull=True) | Q(render_not_before__lte=now)
        )
    claimed = claimable.update(render_claimed_at=now, updated_at=now)
    if claimed != 1:
        return None
    return TtsCardSheet.objects.filter(id=sheet_id, render_claimed_at=now).first()


def get_sheet_with_slots(sheet_id: str) -> TtsCardSheet | None:
    return (
        TtsCardSheet.objects.filter(id=sheet_id)
        .prefetch_related("slots")
        .first()
    )


def get_sheet_rendered_checksums(sheet_ids: list[str]) -> dict[str, str]:
    if not sheet_ids:
        return {}
    return {
        str(sheet_id): str(rendered_checksum)
        for sheet_id, rendered_checksum in TtsCardSheet.objects.filter(id__in=sheet_ids).values_list(
            "id", "rendered_checksum"
        )
    }


def list_all_sheet_ids() -> list[str]:
    return list(TtsCardSheet.objects.order_by("sequence").values_list("id", flat=True))


def list_sheet_ids_needing_render(sheet_ids: list[str]) -> list[str]:
    return list(
        TtsCardSheet.objects.filter(id__in=sheet_ids, desired_revision__gt=F("rendered_revision"))
        .order_by("sequence")
        .values_list("id", flat=True)
    )


def release_render_claim(*, sheet_id: str, claimed_at: datetime | None = None) -> None:
    if claimed_at is None:
        return
    TtsCardSheet.objects.filter(id=sheet_id, render_claimed_at=claimed_at).update(
        render_claimed_at=None,
        updated_at=now_utc(),
    )


def release_expired_render_claims() -> int:
    return TtsCardSheet.objects.filter(
        render_claimed_at__lt=now_utc() - _RENDER_CLAIM_TIMEOUT
    ).update(
        render_claimed_at=None,
        updated_at=now_utc(),
    )


@transaction.atomic
def mark_render_succeeded(
    *,
    sheet_id: str,
    rendered_revision: int,
    rendered_fingerprint: str,
    rendered_checksum: str,
    claimed_at: datetime,
) -> TtsCardSheet | None:
    sheet = (
        TtsCardSheet.objects.select_for_update()
        .filter(id=sheet_id, render_claimed_at=claimed_at)
        .first()
    )
    if sheet is None or sheet.rendered_revision > rendered_revision:
        return None
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
def mark_render_failed(*, sheet_id: str, claimed_at: datetime, error: str) -> bool:
    sheet = (
        TtsCardSheet.objects.select_for_update()
        .filter(id=sheet_id, render_claimed_at=claimed_at)
        .first()
    )
    if sheet is None:
        return False
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
    return True


def _allocate_slot(source: TtsCardImageSource) -> TtsCardSheetSlot:
    for _attempt in range(_SLOT_RESERVATION_ATTEMPTS):
        canonical = TtsCardSheetSlot.objects.filter(card_identity_id=source.card.id).first()
        if canonical is not None:
            return canonical

        sheet = (
            TtsCardSheet.objects.filter(
                layout_version=TTS_CARD_SHEET_LAYOUT_VERSION,
                next_slot_index__lt=TTS_CARD_SHEET_CAPACITY,
            )
            .order_by("-sequence")
            .first()
        )
        if sheet is None:
            try:
                with transaction.atomic():
                    max_sequence = TtsCardSheet.objects.aggregate(value=Max("sequence"))["value"] or 0
                    sheet = TtsCardSheet.objects.create(
                        sequence=max_sequence + 1,
                        layout_version=TTS_CARD_SHEET_LAYOUT_VERSION,
                    )
            except IntegrityError:
                continue

        slot_index = sheet.next_slot_index
        now = now_utc()
        try:
            with transaction.atomic():
                reserved = TtsCardSheet.objects.filter(
                    id=sheet.id,
                    next_slot_index=slot_index,
                    next_slot_index__lt=TTS_CARD_SHEET_CAPACITY,
                ).update(
                    next_slot_index=F("next_slot_index") + 1,
                    updated_at=now,
                )
                if reserved != 1:
                    raise _SlotReservationLost
                return TtsCardSheetSlot.objects.create(
                    sheet=sheet,
                    slot_index=slot_index,
                    card_identity_id=source.card.id,
                    resolved_card=source.card,
                    card_version=source.version,
                    image=source.image,
                    image_checksum=source.image.checksum,
                    image_stored_path=_source_snapshot_path(source),
                )
        except _SlotReservationLost:
            continue
        except IntegrityError:
            canonical = TtsCardSheetSlot.objects.filter(card_identity_id=source.card.id).first()
            if canonical is not None:
                return canonical
    raise TtsCardSheetAllocationError(
        f"Could not reserve a TTS card-sheet slot for Card {source.card.id}."
    )


def _source_snapshot_path(source: TtsCardImageSource) -> str:
    return relativize_storage_path(source.path, preserve_unmatched_absolute=True)


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
    "TtsCardSheetAllocationError",
    "TtsCardSheetAssignment",
    "claim_next_renderable_sheet",
    "claim_sheet_for_render",
    "ensure_sheet_render_requested",
    "get_card_sheet_assignments",
    "get_sheet_rendered_checksums",
    "get_sheet_with_slots",
    "iter_usable_card_source_batches",
    "list_all_sheet_ids",
    "list_sheet_ids_needing_render",
    "list_usable_card_sources",
    "mark_render_failed",
    "mark_render_succeeded",
    "prioritize_sheets",
    "release_expired_render_claims",
    "release_render_claim",
    "request_sheet_rerender",
    "resolve_tts_card_image_path",
    "sync_card_sources",
    "sync_merged_card_source",
]
