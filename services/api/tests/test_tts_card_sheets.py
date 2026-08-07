from __future__ import annotations

from datetime import datetime
from io import BytesIO
from uuid import uuid4

from django.test import Client
from PIL import Image

from card_reader_core.config.settings import settings
from card_reader_core.models import (
    Card,
    CardVersion,
    CardVersionImage,
    Template,
    TtsCardSheet,
    TtsCardSheetSlot,
)
from card_reader_core.services.tts_card_sheets import TtsCardSheetService
from card_reader_core.storage import build_storage_relative_path


def test_assignments_fill_seventy_slots_before_appending_a_sheet() -> None:
    TtsCardSheet.objects.all().delete()
    cards = [_create_sheet_card(f"batch-{index}", color=(index, 30, 60)) for index in range(71)]

    TtsCardSheetService().sync_cards([card.id for card in cards])

    sheets = list(TtsCardSheet.objects.order_by("sequence"))
    assert len(sheets) == 2
    assert sheets[0].next_slot_index == 70
    assert sheets[1].next_slot_index == 1
    assignments = list(
        TtsCardSheetSlot.objects.filter(card_identity_id__in=[card.id for card in cards])
        .select_related("sheet")
        .order_by("sheet__sequence", "slot_index")
    )
    assert [slot.slot_index for slot in assignments[:70]] == list(range(70))
    assert assignments[70].slot_index == 0
    assert assignments[70].sheet_id == sheets[1].id


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
    assert not_modified.status_code == 304
    assert not_modified["ETag"] == second["ETag"]


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


def _create_sheet_card(label: str, *, color: tuple[int, int, int]) -> Card:
    suffix = uuid4().hex
    card = Card.objects.create(
        key=f"tts-sheet-{label}-{suffix}",
        label=f"TTS Sheet {label}",
    )
    version = _create_version(card, label, color=color, version_number=1)
    card.latest_version = version
    card.save(update_fields=["latest_version", "updated_at"])
    return card


def _create_version(
    card: Card,
    label: str,
    *,
    color: tuple[int, int, int],
    version_number: int,
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
    Image.new("RGB", (50, 70), color).save(buffer, format="WEBP")
    path.write_bytes(buffer.getvalue())
    CardVersionImage.objects.create(
        card_version=version,
        source_file=stored_path,
        stored_path=stored_path,
        width=50,
        height=70,
        checksum=f"tts-sheet-{suffix}",
    )
    return version


def _parse_http_date(value: str) -> datetime:
    return datetime.strptime(value, "%a, %d %b %Y %H:%M:%S GMT")
