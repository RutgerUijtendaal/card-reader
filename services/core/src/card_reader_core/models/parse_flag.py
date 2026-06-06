from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser
    from django.db.models.manager import Manager

    from .card_version import CardVersion


PARSE_FLAG_PROPERTY_KEYS = (
    "name",
    "type_line",
    "mana_cost",
    "attack",
    "health",
    "rules_text",
    "keywords",
    "tags",
    "types",
    "symbols",
    "other",
)
PARSE_FLAG_ITEM_OPEN = "open"
PARSE_FLAG_ITEM_RESOLVED = "resolved"
PARSE_FLAG_ITEM_DISMISSED = "dismissed"
PARSE_FLAG_ITEM_STATUSES = (
    PARSE_FLAG_ITEM_OPEN,
    PARSE_FLAG_ITEM_RESOLVED,
    PARSE_FLAG_ITEM_DISMISSED,
)


class CardVersionParseFlag(TimestampedModel):
    if TYPE_CHECKING:
        items: Manager[CardVersionParseFlagItem]

    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card_version: models.ForeignKey[CardVersion, CardVersion] = models.ForeignKey(
        "CardVersion",
        on_delete=models.CASCADE,
        related_name="parse_flags",
        db_column="card_version_id",
    )
    submitted_by: models.ForeignKey[AbstractUser, AbstractUser] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="card_version_parse_flags",
        db_column="submitted_by_id",
    )
    note: models.TextField[str, str] = models.TextField(default="", blank=True)

    class Meta:
        db_table = "card_version_parse_flag"
        indexes = [
            models.Index(fields=["card_version", "created_at"], name="ix_parse_flag_version_created"),
            models.Index(fields=["submitted_by", "created_at"], name="ix_parse_flag_user_created"),
        ]


class CardVersionParseFlagItem(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    flag: models.ForeignKey[CardVersionParseFlag, CardVersionParseFlag] = models.ForeignKey(
        "CardVersionParseFlag",
        on_delete=models.CASCADE,
        related_name="items",
        db_column="flag_id",
    )
    property_key: models.TextField[str, str] = models.TextField(db_index=True)
    captured_current_value: models.TextField[str, str] = models.TextField(default="", blank=True)
    expected_value: models.TextField[str, str] = models.TextField(default="", blank=True)
    note: models.TextField[str, str] = models.TextField(default="", blank=True)
    status: models.TextField[str, str] = models.TextField(default=PARSE_FLAG_ITEM_OPEN, db_index=True)
    reviewed_by: models.ForeignKey[AbstractUser | None, AbstractUser | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_card_version_parse_flag_items",
        db_column="reviewed_by_id",
        default=None,
        null=True,
        blank=True,
    )
    review_note: models.TextField[str, str] = models.TextField(default="", blank=True)
    reviewed_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "card_version_parse_flag_item"
        indexes = [
            models.Index(fields=["status", "created_at"], name="ix_parse_flag_item_status_created"),
            models.Index(fields=["property_key", "status"], name="ix_parse_flag_item_prop_status"),
        ]
