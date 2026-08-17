from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

    from .card import Card
    from .card_version import CardVersion
    from .import_job import ImportJobItem


CLASSIFICATION_REVIEW_OPEN = "open"
CLASSIFICATION_REVIEW_RESOLVED = "resolved"
CLASSIFICATION_REVIEW_DISMISSED = "dismissed"
CLASSIFICATION_REVIEW_STATUSES = (
    CLASSIFICATION_REVIEW_OPEN,
    CLASSIFICATION_REVIEW_RESOLVED,
    CLASSIFICATION_REVIEW_DISMISSED,
)


class CardClassificationReviewItem(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    import_item: models.OneToOneField[ImportJobItem, ImportJobItem] = models.OneToOneField(
        "ImportJobItem",
        on_delete=models.CASCADE,
        related_name="classification_review_item",
        db_column="import_item_id",
    )
    card: models.ForeignKey[Card | None, Card | None] = models.ForeignKey(
        "Card",
        on_delete=models.SET_NULL,
        related_name="classification_review_items",
        db_column="card_id",
        null=True,
        blank=True,
    )
    card_version: models.ForeignKey[CardVersion | None, CardVersion | None] = models.ForeignKey(
        "CardVersion",
        on_delete=models.SET_NULL,
        related_name="classification_review_items",
        db_column="card_version_id",
        null=True,
        blank=True,
    )
    card_pool: models.TextField[str, str] = models.TextField(db_index=True)
    existing_classification_json = models.JSONField(default=dict)
    inferred_classification_json = models.JSONField(default=dict)
    inference_evidence_json = models.JSONField(default=dict)
    status: models.TextField[str, str] = models.TextField(
        default=CLASSIFICATION_REVIEW_OPEN,
        db_index=True,
    )
    reviewed_by: models.ForeignKey[AbstractUser | None, AbstractUser | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_card_classification_items",
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
        db_table = "card_classification_review_item"
        indexes = [
            models.Index(
                fields=["status", "created_at"],
                name="ix_class_review_status_created",
            ),
            models.Index(
                fields=["card_pool", "status"],
                name="ix_class_review_pool_status",
            ),
        ]
