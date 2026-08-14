from __future__ import annotations

from django.db import models

from .base import TimestampedModel, uuid_str


class Template(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    key: models.TextField[str, str] = models.TextField(default="", db_index=True, unique=True)
    label: models.TextField[str, str] = models.TextField(default="")
    definition_json = models.JSONField(default=dict)

    class Meta:
        db_table = "template"
