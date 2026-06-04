from __future__ import annotations

from django.db import models

from .base import TimestampedModel, uuid_str


class ContentVersion(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    version_number: models.TextField[str, str] = models.TextField(unique=True)
    base_version: models.TextField[str, str] = models.TextField(db_index=True)
    major: models.IntegerField[int, int] = models.IntegerField(db_index=True)
    minor: models.IntegerField[int, int] = models.IntegerField(db_index=True)
    patch: models.IntegerField[int, int] = models.IntegerField(db_index=True)
    description: models.TextField[str, str] = models.TextField()

    class Meta:
        db_table = "content_version"
        indexes = [
            models.Index(fields=["major", "minor", "patch"], name="ix_content_version_semver"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("major", "minor", "patch"),
                name="ux_content_version_semver",
            )
        ]
