from __future__ import annotations

from django.db import models

from .base import TimestampedModel, uuid_str


class Card(TimestampedModel):
    id = models.TextField(default=uuid_str, primary_key=True)
    key = models.TextField(default="", db_index=True, unique=True)
    label = models.TextField(default="")
    latest_version_id = models.TextField(default=None, null=True, db_index=True)

    class Meta:
        db_table = "card"


