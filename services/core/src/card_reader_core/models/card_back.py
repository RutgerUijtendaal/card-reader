from __future__ import annotations

from django.db import models
from django.db.models import Q

from .base import TimestampedModel, uuid_str


class CardBack(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    label: models.TextField[str, str] = models.TextField(default="")
    original_filename: models.TextField[str, str] = models.TextField(default="")
    source_file: models.TextField[str, str] = models.TextField()
    stored_path: models.TextField[str, str] = models.TextField()
    width: models.IntegerField[int, int] = models.IntegerField(default=0)
    height: models.IntegerField[int, int] = models.IntegerField(default=0)
    checksum: models.TextField[str, str] = models.TextField(db_index=True)
    is_current: models.BooleanField[bool, bool] = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "card_back"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_current"],
                condition=Q(is_current=True),
                name="ux_card_back_single_current",
            )
        ]
