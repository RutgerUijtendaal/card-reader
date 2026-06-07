from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


NOTIFICATION_STATUS_UNREAD = "unread"
NOTIFICATION_STATUS_READ = "read"
NOTIFICATION_STATUS_ALL = "all"
NOTIFICATION_STATUS_FILTERS = (
    NOTIFICATION_STATUS_UNREAD,
    NOTIFICATION_STATUS_READ,
    NOTIFICATION_STATUS_ALL,
)

NOTIFICATION_EVENT_PARSE_FLAG_REVIEWED = "parse_flag.reviewed"
NOTIFICATION_EVENT_DECK_CARD_CHANGED = "deck.card_changed"


class UserNotification(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    recipient: models.ForeignKey[AbstractUser, AbstractUser] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_column="recipient_id",
    )
    actor: models.ForeignKey[AbstractUser | None, AbstractUser | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="triggered_notifications",
        db_column="actor_id",
        default=None,
        null=True,
        blank=True,
    )
    event_type: models.TextField[str, str] = models.TextField(db_index=True)
    subject_type: models.TextField[str, str] = models.TextField(default="", blank=True, db_index=True)
    subject_id: models.TextField[str, str] = models.TextField(default="", blank=True, db_index=True)
    target_url: models.TextField[str, str] = models.TextField(default="", blank=True)
    title: models.TextField[str, str] = models.TextField(default="")
    message: models.TextField[str, str] = models.TextField(default="", blank=True)
    metadata_json: models.JSONField[dict[str, object], dict[str, object]] = models.JSONField(default=dict)
    dedupe_key: models.TextField[str, str] = models.TextField(default="", blank=True, db_index=True)
    event_count: models.IntegerField[int, int] = models.IntegerField(default=1)
    read_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
    )
    archived_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
    )
    last_event_at: models.DateTimeField[datetime, datetime] = models.DateTimeField()

    class Meta:
        db_table = "user_notification"
        indexes = [
            models.Index(fields=["recipient", "read_at", "-last_event_at"], name="ix_notification_recipient_read"),
            models.Index(fields=["recipient", "dedupe_key", "read_at"], name="ix_notification_recipient_dedupe"),
            models.Index(fields=["event_type", "subject_type", "subject_id"], name="ix_notification_subject"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "dedupe_key"],
                condition=models.Q(dedupe_key__gt="", read_at__isnull=True, archived_at__isnull=True),
                name="ux_notification_active_dedupe",
            ),
        ]
