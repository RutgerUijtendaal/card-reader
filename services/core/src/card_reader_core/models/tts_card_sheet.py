from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import F, Q

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from django.db.models.manager import Manager

    from .card import Card
    from .card_version import CardVersion, CardVersionImage


TTS_CARD_SHEET_LAYOUT_VERSION = 3
TTS_CARD_SHEET_COLUMNS = 9
TTS_CARD_SHEET_ROWS = 7
TTS_CARD_SHEET_CAPACITY = TTS_CARD_SHEET_COLUMNS * TTS_CARD_SHEET_ROWS


class TtsCardSheet(TimestampedModel):
    if TYPE_CHECKING:
        slots: Manager[TtsCardSheetSlot]

    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    sequence: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(unique=True)
    layout_version: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField(
        default=TTS_CARD_SHEET_LAYOUT_VERSION
    )
    next_slot_index: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField(
        default=0
    )
    desired_revision: models.PositiveBigIntegerField[int, int] = models.PositiveBigIntegerField(
        default=0
    )
    desired_fingerprint: models.TextField[str, str] = models.TextField(default="")
    rendered_revision: models.PositiveBigIntegerField[int, int] = models.PositiveBigIntegerField(
        default=0
    )
    rendered_fingerprint: models.TextField[str, str] = models.TextField(default="")
    rendered_checksum: models.TextField[str, str] = models.TextField(default="")
    published_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        default=None, null=True
    )
    dirty_since: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        default=None, null=True
    )
    render_not_before: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        default=None, null=True, db_index=True
    )
    render_claimed_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        default=None, null=True, db_index=True
    )
    render_failure_count: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(
        default=0
    )
    render_priority: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField(
        default=0
    )
    last_render_error: models.TextField[str, str] = models.TextField(default="")

    class Meta:
        db_table = "tts_card_sheet"
        ordering = ["sequence"]
        indexes = [
            models.Index(
                fields=["-render_priority", "render_not_before", "render_claimed_at", "sequence"],
                name="ix_tts_sheet_render_queue",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(next_slot_index__lte=TTS_CARD_SHEET_CAPACITY),
                name="ck_tts_sheet_next_slot_capacity",
            ),
            models.CheckConstraint(
                condition=Q(rendered_revision__lte=F("desired_revision")),
                name="ck_tts_sheet_rendered_revision",
            ),
        ]


class TtsCardSheetSlot(TimestampedModel):
    if TYPE_CHECKING:
        sheet_id: str
        resolved_card_id: str | None
        card_version_id: str | None
        image_id: str | None

    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    sheet: models.ForeignKey[TtsCardSheet, TtsCardSheet] = models.ForeignKey(
        TtsCardSheet,
        on_delete=models.CASCADE,
        related_name="slots",
        db_column="sheet_id",
    )
    slot_index: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField()
    card_identity_id: models.TextField[str, str] = models.TextField(unique=True)
    resolved_card: models.ForeignKey[Card | None, Card | None] = models.ForeignKey(
        "Card",
        on_delete=models.SET_NULL,
        related_name="+",
        db_column="resolved_card_id",
        default=None,
        null=True,
    )
    card_version: models.ForeignKey[CardVersion | None, CardVersion | None] = models.ForeignKey(
        "CardVersion",
        on_delete=models.SET_NULL,
        related_name="+",
        db_column="card_version_id",
        default=None,
        null=True,
    )
    image: models.ForeignKey[CardVersionImage | None, CardVersionImage | None] = models.ForeignKey(
        "CardVersionImage",
        on_delete=models.SET_NULL,
        related_name="+",
        db_column="image_id",
        default=None,
        null=True,
    )
    image_checksum: models.TextField[str, str] = models.TextField(default="")
    image_stored_path: models.TextField[str, str] = models.TextField(default="")

    class Meta:
        db_table = "tts_card_sheet_slot"
        ordering = ["sheet__sequence", "slot_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["sheet", "slot_index"],
                name="ux_tts_sheet_slot_position",
            ),
            models.CheckConstraint(
                condition=Q(slot_index__lt=TTS_CARD_SHEET_CAPACITY),
                name="ck_tts_sheet_slot_capacity",
            ),
        ]
