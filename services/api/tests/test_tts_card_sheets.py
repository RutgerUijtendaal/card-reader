from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from io import BytesIO
import os
from pathlib import Path
import time
from uuid import uuid4

import pytest
from django.db import close_old_connections
from django.test import Client
from PIL import Image

from card_reader_api.management.commands.run_tts_sheet_renderer import _process_claimed_sheet
from card_reader_core.config.settings import settings
from card_reader_core.models import (
    TTS_CARD_SHEET_LAYOUT_VERSION,
    Card,
    CardVersion,
    CardVersionImage,
    Template,
    TtsCardSheet,
    TtsCardSheetSlot,
    now_utc,
)
from card_reader_core.services.card_merges import merge_cards
from card_reader_core.repositories.tts_card_sheets import (
    claim_next_renderable_sheet,
    claim_sheet_for_render,
    prioritize_sheets,
    release_render_claim,
)
from card_reader_core.services.tts_card_sheets import (
    TtsCardSheetPreparationError,
    TtsCardSheetService,
)
from card_reader_core.services.tts_card_sheets import renderer as tts_sheet_renderer
from card_reader_core.services.tts_card_sheets import service as tts_sheet_service
from card_reader_core.storage import build_storage_relative_path


def test_assignments_fill_sixty_three_slots_before_appending_a_sheet() -> None:
    TtsCardSheet.objects.all().delete()
    cards = [_create_sheet_card(f"batch-{index}", color=(index, 30, 60)) for index in range(64)]

    TtsCardSheetService().sync_cards([card.id for card in cards])

    sheets = list(TtsCardSheet.objects.order_by("sequence"))
    assert len(sheets) == 2
    assert sheets[0].next_slot_index == 63
    assert sheets[1].next_slot_index == 1
    assignments = list(
        TtsCardSheetSlot.objects.filter(card_identity_id__in=[card.id for card in cards])
        .select_related("sheet")
        .order_by("sheet__sequence", "slot_index")
    )
    assert [slot.slot_index for slot in assignments[:63]] == list(range(63))
    assert assignments[63].slot_index == 0
    assert assignments[63].sheet_id == sheets[1].id


def test_unreadable_images_are_not_assigned_to_sheets() -> None:
    TtsCardSheet.objects.all().delete()
    card = _create_sheet_card("unreadable", color=(20, 30, 40))
    version = card.latest_version
    assert version is not None
    image = version.images.get()
    (settings.storage_root_dir / image.stored_path).write_bytes(b"not-an-image")

    sheet_ids = TtsCardSheetService().sync_cards([card.id])

    assert sheet_ids == set()
    assert not TtsCardSheetSlot.objects.filter(card_identity_id=card.id).exists()


def test_game_master_cards_are_not_allocated_to_public_tts_sheets() -> None:
    TtsCardSheet.objects.all().delete()
    card = _create_sheet_card("game-master-source", color=(20, 30, 40))
    card.card_pool = "game_master"
    card.save(update_fields=["card_pool"])

    sheet_ids = TtsCardSheetService().sync_cards([card.id])

    assert sheet_ids == set()
    assert not TtsCardSheetSlot.objects.filter(card_identity_id=card.id).exists()


def test_assignment_snapshots_the_readable_source_file_fallback() -> None:
    TtsCardSheet.objects.all().delete()
    card = _create_sheet_card("source-fallback", color=(30, 40, 50))
    version = card.latest_version
    assert version is not None
    image = version.images.get()
    stored_path = settings.storage_root_dir / image.stored_path
    fallback_path = build_storage_relative_path("uploads", f"tts-fallback-{uuid4().hex}.webp")
    fallback_file = settings.storage_root_dir / fallback_path
    fallback_file.parent.mkdir(parents=True, exist_ok=True)
    fallback_file.write_bytes(stored_path.read_bytes())
    stored_path.unlink()
    image.stored_path = build_storage_relative_path("images", f"missing-{uuid4().hex}.webp")
    image.source_file = fallback_path
    image.save(update_fields=["stored_path", "source_file", "updated_at"])

    TtsCardSheetService().sync_cards([card.id])

    slot = TtsCardSheetSlot.objects.get(card_identity_id=card.id)
    assert slot.image_stored_path == fallback_path


def test_merge_rebinds_source_slots_when_target_artwork_is_unreadable() -> None:
    TtsCardSheet.objects.all().delete()
    target = _create_sheet_card("merge-target", color=(10, 20, 30))
    source = _create_sheet_card("merge-source", color=(70, 80, 90))
    target_version = target.latest_version
    source_version = source.latest_version
    assert target_version is not None
    assert source_version is not None
    target_image = target_version.images.get()
    (settings.storage_root_dir / target_image.stored_path).write_bytes(b"not-an-image")
    TtsCardSheetService().sync_cards([source.id])
    source_slot = TtsCardSheetSlot.objects.get(card_identity_id=source.id)
    original_checksum = source_slot.image_checksum
    original_path = source_slot.image_stored_path

    merge_cards(target_card_id=target.id, source_card_ids=[source.id])

    source_slot.refresh_from_db()
    assert source_slot.resolved_card_id == target.id
    assert source_slot.card_version_id == source_version.id
    assert source_slot.image_checksum == original_checksum
    assert source_slot.image_stored_path == original_path
    assert not Card.objects.filter(id=source.id).exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_allocation_reserves_unique_sqlite_slots() -> None:
    TtsCardSheet.objects.all().delete()
    cards = [
        _create_sheet_card(f"concurrent-{index}", color=(index, 50, 70))
        for index in range(12)
    ]

    def sync_card(card_id: str) -> None:
        close_old_connections()
        try:
            TtsCardSheetService().sync_cards([card_id])
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(sync_card, [card.id for card in cards]))

    slots = list(
        TtsCardSheetSlot.objects.filter(card_identity_id__in=[card.id for card in cards])
        .order_by("slot_index")
        .values_list("slot_index", flat=True)
    )
    assert slots == list(range(12))
    assert TtsCardSheet.objects.get().next_slot_index == 12


@pytest.mark.django_db(transaction=True)
def test_concurrent_sqlite_render_claims_have_one_winner() -> None:
    TtsCardSheet.objects.all().delete()
    sheet = TtsCardSheet.objects.create(
        sequence=999_995,
        desired_revision=1,
        rendered_revision=0,
        render_not_before=now_utc() - timedelta(seconds=1),
    )

    def claim_sheet(_index: int) -> str | None:
        close_old_connections()
        try:
            claimed = claim_next_renderable_sheet()
            return str(claimed.id) if claimed is not None else None
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=4) as executor:
        claimed_ids = list(executor.map(claim_sheet, range(4)))

    assert claimed_ids.count(str(sheet.id)) == 1
    assert claimed_ids.count(None) == 3


def test_prioritization_and_inline_claim_preserve_active_failure_backoff() -> None:
    TtsCardSheet.objects.all().delete()
    render_not_before = now_utc() + timedelta(minutes=2)
    sheet = TtsCardSheet.objects.create(
        sequence=999_994,
        desired_revision=1,
        rendered_revision=0,
        render_failure_count=3,
        render_not_before=render_not_before,
    )

    prioritize_sheets([str(sheet.id)])
    claimed = claim_sheet_for_render(str(sheet.id), respect_not_before=True)

    sheet.refresh_from_db()
    assert claimed is None
    assert sheet.render_priority == 1
    assert sheet.render_not_before == render_not_before


@pytest.mark.django_db(transaction=True)
def test_public_sheet_endpoint_changes_headers_and_bytes_after_latest_artwork_changes() -> None:
    TtsCardSheet.objects.all().delete()
    card = _create_sheet_card("refresh", color=(20, 40, 60))
    service = TtsCardSheetService()
    sheet_ids = service.sync_cards([card.id])
    service.render_sheets_now(sorted(sheet_ids))
    sheet = TtsCardSheet.objects.get(id=next(iter(sheet_ids)))
    client = Client(HTTP_HOST="localhost")

    first = client.get(f"/tts/card-sheets/{sheet.id}/image.webp")
    first_body = b"".join(first.streaming_content)
    first_modified = _parse_http_date(first["Last-Modified"])
    first.close()

    previous = card.latest_version
    assert previous is not None
    previous.is_latest = False
    previous.save(update_fields=["is_latest", "updated_at"])
    latest = _create_version(card, "refresh-latest", color=(180, 20, 40), version_number=2)
    card.latest_version = latest
    card.save(update_fields=["latest_version", "updated_at"])
    changed_sheet_ids = service.sync_cards([card.id])
    service.render_sheets_now(sorted(changed_sheet_ids))

    second = client.get(f"/tts/card-sheets/{sheet.id}/image.webp")
    second_body = b"".join(second.streaming_content)
    second.close()
    head = client.head(f"/tts/card-sheets/{sheet.id}/image.webp")
    not_modified = client.get(
        f"/tts/card-sheets/{sheet.id}/image.webp",
        HTTP_IF_NONE_MATCH=second["ETag"],
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first["Cache-Control"] == "public, no-cache"
    assert first["ETag"] != second["ETag"]
    assert first_body != second_body
    assert _parse_http_date(second["Last-Modified"]) > first_modified
    assert head["ETag"] == second["ETag"]
    assert head["Last-Modified"] == second["Last-Modified"]
    assert head["Content-Type"] == "image/webp"
    assert head.content == b""
    head.close()
    assert not_modified.status_code == 304
    assert not_modified["ETag"] == second["ETag"]
    not_modified.close()


@pytest.mark.django_db(transaction=True)
def test_reclassifying_a_player_card_revokes_old_public_tts_artwork_until_rerendered() -> None:
    TtsCardSheet.objects.all().delete()
    card = _create_sheet_card("reclassified", color=(120, 40, 60))
    service = TtsCardSheetService()
    sheet_ids = service.sync_cards([card.id])
    service.render_sheets_now(sorted(sheet_ids))
    sheet_id = next(iter(sheet_ids))
    client = Client(HTTP_HOST="localhost")

    card.card_pool = "game_master"
    card.save(update_fields=["card_pool"])
    service.sync_cards([card.id])

    preparing = client.get(f"/tts/card-sheets/{sheet_id}/image.webp")
    assert preparing.status_code == 503

    service.render_sheets_now([sheet_id])
    response = client.get(f"/tts/card-sheets/{sheet_id}/image.webp")
    body = b"".join(response.streaming_content)
    response.close()
    with Image.open(BytesIO(body)) as rendered:
        assert rendered.getpixel((10, 10)) == (0, 0, 0)


@pytest.mark.django_db(transaction=True)
def test_failed_metadata_publish_keeps_previous_sheet_revision_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    TtsCardSheet.objects.all().delete()
    card = _create_sheet_card("atomic-publish", color=(20, 40, 60))
    service = TtsCardSheetService()
    sheet_ids = service.sync_cards([card.id])
    service.render_sheets_now(sorted(sheet_ids))
    sheet = TtsCardSheet.objects.get(id=next(iter(sheet_ids)))
    client = Client(HTTP_HOST="localhost")
    first = client.get(f"/tts/card-sheets/{sheet.id}/image.webp")
    first_body = b"".join(first.streaming_content)
    first.close()

    previous = card.latest_version
    assert previous is not None
    previous.is_latest = False
    previous.save(update_fields=["is_latest", "updated_at"])
    latest = _create_version(
        card,
        "atomic-publish-latest",
        color=(180, 20, 40),
        version_number=2,
    )
    card.latest_version = latest
    card.save(update_fields=["latest_version", "updated_at"])
    changed_sheet_ids = service.sync_cards([card.id])

    def fail_metadata_publish(**_kwargs: object) -> TtsCardSheet:
        raise RuntimeError("database write failed")

    monkeypatch.setattr(tts_sheet_renderer, "mark_render_succeeded", fail_metadata_publish)
    with pytest.raises(tts_sheet_renderer.TtsCardSheetRenderError, match="database write failed"):
        service.render_sheets_now(sorted(changed_sheet_ids))

    second = client.get(f"/tts/card-sheets/{sheet.id}/image.webp")
    second_body = b"".join(second.streaming_content)
    second.close()
    assert second.status_code == 200
    assert second["ETag"] == first["ETag"]
    assert second["Last-Modified"] == first["Last-Modified"]
    assert second_body == first_body


def test_renderer_recovery_releases_expired_claims() -> None:
    TtsCardSheet.objects.all().delete()
    claimed_at = now_utc() - timedelta(minutes=11)
    sheet = TtsCardSheet.objects.create(
        sequence=999_997,
        desired_revision=1,
        rendered_revision=0,
        render_claimed_at=claimed_at,
    )

    TtsCardSheetService().recover_renderer()

    sheet.refresh_from_db()
    assert sheet.render_claimed_at is None


def test_renderer_recovery_preserves_live_claims() -> None:
    TtsCardSheet.objects.all().delete()
    claimed_at = now_utc()
    sheet = TtsCardSheet.objects.create(
        sequence=999_993,
        desired_revision=1,
        rendered_revision=0,
        render_claimed_at=claimed_at,
    )

    TtsCardSheetService().recover_renderer()

    sheet.refresh_from_db()
    assert sheet.render_claimed_at == claimed_at


def test_stale_renderer_cannot_publish_over_a_new_claim() -> None:
    TtsCardSheet.objects.all().delete()
    sheet = TtsCardSheet.objects.create(
        sequence=999_992,
        desired_revision=1,
        rendered_revision=0,
        render_not_before=now_utc() - timedelta(seconds=1),
    )
    stale_claim = claim_sheet_for_render(str(sheet.id))
    assert stale_claim is not None
    release_render_claim(
        sheet_id=str(sheet.id),
        claimed_at=stale_claim.render_claimed_at,
    )
    current_claim = claim_sheet_for_render(str(sheet.id))
    assert current_claim is not None

    with pytest.raises(tts_sheet_renderer.TtsCardSheetRenderLeaseLost):
        tts_sheet_renderer.render_claimed_sheet(stale_claim)

    sheet.refresh_from_db()
    assert sheet.render_claimed_at == current_claim.render_claimed_at
    assert sheet.rendered_revision == 0


def test_renderer_directory_setup_failure_releases_claim_and_applies_backoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    TtsCardSheet.objects.all().delete()
    card = _create_sheet_card("directory-failure", color=(35, 45, 55))
    service = TtsCardSheetService()
    service.sync_cards([card.id])
    assignment = TtsCardSheetSlot.objects.get(card_identity_id=card.id)
    claimed = claim_sheet_for_render(assignment.sheet_id)
    assert claimed is not None
    blocked_storage_root = tmp_path / "blocked-storage-root"
    blocked_storage_root.write_bytes(b"not a directory")
    monkeypatch.setattr(settings, "app_data_dir", blocked_storage_root)

    with pytest.raises(tts_sheet_renderer.TtsCardSheetRenderError):
        tts_sheet_renderer.render_claimed_sheet(claimed)

    claimed.refresh_from_db()
    assert claimed.render_claimed_at is None
    assert claimed.render_failure_count == 1
    assert claimed.render_not_before is not None


def test_reconciliation_includes_unreferenced_persisted_sheets() -> None:
    TtsCardSheet.objects.all().delete()
    sheet = TtsCardSheet.objects.create(
        sequence=999_991,
        desired_revision=0,
        rendered_revision=0,
    )

    result = TtsCardSheetService().reconcile_all(render=False)

    sheet.refresh_from_db()
    assert result.affected_sheets >= 1
    assert sheet.desired_revision == 1


def test_reconciliation_upgrades_legacy_layout_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    TtsCardSheet.objects.all().delete()
    monkeypatch.setattr(tts_sheet_service, "iter_usable_card_source_batches", lambda: ())
    sheet = TtsCardSheet.objects.create(
        sequence=999_990,
        layout_version=2,
        desired_revision=4,
        desired_fingerprint="legacy-layout",
        rendered_revision=4,
        rendered_fingerprint="legacy-layout",
        rendered_checksum="published-sheet",
    )
    service = TtsCardSheetService()

    first = service.reconcile_all(render=False)

    sheet.refresh_from_db()
    first_revision = sheet.desired_revision
    assert sheet.layout_version == TTS_CARD_SHEET_LAYOUT_VERSION
    assert first.affected_sheets == 1
    assert first_revision == 5
    assert sheet.rendered_revision == 4
    assert sheet.rendered_checksum == "published-sheet"

    service.reconcile_all(render=False)

    sheet.refresh_from_db()
    assert sheet.desired_revision == first_revision


def test_current_layout_uses_canonical_images_without_resizing_or_letterboxing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    TtsCardSheet.objects.all().delete()
    color = (40, 80, 120)
    card = _create_sheet_card("canonical-ratio", color=color, image_size=(822, 1122))
    service = TtsCardSheetService()
    sheet_ids = service.sync_cards([card.id])

    def reject_resize(*args: object, **kwargs: object) -> Image.Image:
        raise AssertionError("Canonical card images must not be resized")

    monkeypatch.setattr(tts_sheet_renderer.ImageOps, "contain", reject_resize)

    assert service.render_sheets_now(sorted(sheet_ids)) == 1

    sheet = TtsCardSheet.objects.get(id=next(iter(sheet_ids)))
    layout = tts_sheet_renderer.get_tts_card_sheet_layout(sheet.layout_version)
    path = tts_sheet_renderer.tts_card_sheet_path(str(sheet.id), sheet.rendered_checksum)
    with Image.open(path) as rendered:
        assert rendered.size == (7398, 7854)
        assert max(rendered.size) <= 8192
        assert (layout.cell_width, layout.cell_height) == (822, 1122)
        top_pixel = rendered.getpixel((layout.cell_width // 2, 0))
        middle_pixel = rendered.getpixel(
            (layout.cell_width // 2, layout.cell_height // 2)
        )
        bottom_pixel = rendered.getpixel(
            (layout.cell_width // 2, layout.cell_height - 1)
        )
    assert all(
        abs(actual - expected) <= 8 for actual, expected in zip(middle_pixel, color)
    )
    for edge_pixel in (top_pixel, bottom_pixel):
        assert sum(edge_pixel) >= sum(middle_pixel) // 2


def test_renderer_stop_releases_the_claim_before_processing() -> None:
    TtsCardSheet.objects.all().delete()
    claimed_at = now_utc()
    sheet = TtsCardSheet.objects.create(
        sequence=999_996,
        desired_revision=1,
        rendered_revision=0,
        render_claimed_at=claimed_at,
    )

    _process_claimed_sheet(sheet, lambda: True)

    sheet.refresh_from_db()
    assert sheet.render_claimed_at is None
    assert sheet.rendered_revision == 0


def test_superseded_sheet_revision_cleanup_keeps_only_current_and_previous(
    tmp_path: Path,
) -> None:
    sheet_id = str(uuid4())
    oldest = tmp_path / f"{sheet_id}.oldest.webp"
    previous = tmp_path / f"{sheet_id}.previous.webp"
    current = tmp_path / f"{sheet_id}.current.webp"
    base_timestamp = time.time() - 60
    for index, path in enumerate((oldest, previous, current), start=1):
        path.write_bytes(str(index).encode("ascii"))
        timestamp = base_timestamp + index
        os.utime(path, times=(timestamp, timestamp))

    tts_sheet_renderer._remove_superseded_sheet_revisions(
        sheet_id=sheet_id,
        current_path=current,
    )

    assert not oldest.exists()
    assert previous.exists()
    assert current.exists()


def test_prepare_cards_translates_synchronous_render_failures() -> None:
    TtsCardSheet.objects.all().delete()
    selected = _create_sheet_card("selected-render-failure", color=(20, 30, 40))
    broken_neighbor = _create_sheet_card("neighbor-render-failure", color=(50, 60, 70))
    service = TtsCardSheetService()
    service.sync_cards([selected.id, broken_neighbor.id])
    broken_slot = TtsCardSheetSlot.objects.get(card_identity_id=broken_neighbor.id)
    (settings.storage_root_dir / broken_slot.image_stored_path).unlink()

    with pytest.raises(TtsCardSheetPreparationError, match="could not be rendered"):
        service.prepare_cards([selected.id], timeout_seconds=0)


def test_prepare_cards_does_not_wait_for_renderer_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    TtsCardSheet.objects.all().delete()
    selected = _create_sheet_card("production-pending", color=(25, 35, 45))
    storage_root = settings.storage_root_dir
    monkeypatch.setattr(settings, "app_data_dir", storage_root)
    monkeypatch.setattr(settings, "environment", "production")

    def fail_if_waited(
        _service: TtsCardSheetService,
        _sheet_ids: list[str],
        *,
        timeout_seconds: float,
    ) -> None:
        raise AssertionError(f"Production preparation waited for {timeout_seconds} seconds.")

    monkeypatch.setattr(TtsCardSheetService, "_wait_until_ready", fail_if_waited)

    with pytest.raises(TtsCardSheetPreparationError, match="still being prepared"):
        TtsCardSheetService().prepare_cards([selected.id])


def test_unknown_and_unrendered_sheet_responses_are_explicit() -> None:
    TtsCardSheet.objects.all().delete()
    unknown = Client(HTTP_HOST="localhost").get(
        "/tts/card-sheets/00000000-0000-0000-0000-000000000000/image.webp"
    )
    sheet = TtsCardSheet.objects.create(sequence=999_999)
    pending = Client(HTTP_HOST="localhost").head(
        f"/tts/card-sheets/{sheet.id}/image.webp"
    )

    assert unknown.status_code == 404
    assert pending.status_code == 503
    assert pending["Retry-After"] == "2"


def test_public_sheet_request_preserves_failure_backoff() -> None:
    TtsCardSheet.objects.all().delete()
    render_not_before = now_utc() + timedelta(minutes=2)
    sheet = TtsCardSheet.objects.create(
        sequence=999_998,
        desired_revision=1,
        rendered_revision=0,
        render_failure_count=3,
        render_not_before=render_not_before,
    )

    response = Client(HTTP_HOST="localhost").head(
        f"/tts/card-sheets/{sheet.id}/image.webp"
    )

    sheet.refresh_from_db()
    assert response.status_code == 503
    assert sheet.render_not_before == render_not_before


def _create_sheet_card(
    label: str,
    *,
    color: tuple[int, int, int],
    image_size: tuple[int, int] = (50, 70),
) -> Card:
    suffix = uuid4().hex
    card = Card.objects.create(
        key=f"tts-sheet-{label}-{suffix}",
        label=f"TTS Sheet {label}",
    )
    version = _create_version(
        card,
        label,
        color=color,
        version_number=1,
        image_size=image_size,
    )
    card.latest_version = version
    card.save(update_fields=["latest_version", "updated_at"])
    return card


def _create_version(
    card: Card,
    label: str,
    *,
    color: tuple[int, int, int],
    version_number: int,
    image_size: tuple[int, int] = (50, 70),
) -> CardVersion:
    suffix = uuid4().hex
    version = CardVersion.objects.create(
        card=card,
        version_number=version_number,
        template=Template.objects.get(key="mtg-like-v1"),
        image_hash=f"tts-sheet-{label}-{suffix}",
        name=f"TTS Sheet {label}",
        is_latest=True,
    )
    stored_path = build_storage_relative_path("images", f"tts-sheet-{suffix}.webp")
    path = settings.storage_root_dir / stored_path
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = BytesIO()
    Image.new("RGB", image_size, color).save(buffer, format="WEBP")
    path.write_bytes(buffer.getvalue())
    CardVersionImage.objects.create(
        card_version=version,
        source_file=stored_path,
        stored_path=stored_path,
        width=image_size[0],
        height=image_size[1],
        checksum=f"tts-sheet-{suffix}",
    )
    return version


def _parse_http_date(value: str) -> datetime:
    return datetime.strptime(value, "%a, %d %b %Y %H:%M:%S GMT")
