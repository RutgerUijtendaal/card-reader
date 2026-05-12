from __future__ import annotations

from django.db import models

from .base import TimestampedModel, uuid_str


class Card(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    key: models.TextField[str, str] = models.TextField(default="", db_index=True, unique=True)
    label: models.TextField[str, str] = models.TextField(default="")
    latest_version = models.ForeignKey(
        "CardVersion",
        on_delete=models.SET_NULL,
        related_name="+",
        db_column="latest_version_id",
        default=None,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "card"


