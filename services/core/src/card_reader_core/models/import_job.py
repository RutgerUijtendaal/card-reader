from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from django.db import models

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from .card import Card
    from .card_version import CardVersion
    from .content_version import ContentVersion
    from .template import Template


class ImportJobStatus(StrEnum):
    queued = "queued"
    running = "running"
    canceling = "canceling"
    cancelled = "cancelled"
    completed = "completed"
    failed = "failed"


class ImportJob(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    source_path: models.TextField[str, str] = models.TextField()
    template: models.ForeignKey[Template, Template] = models.ForeignKey(
        "Template",
        on_delete=models.PROTECT,
        related_name="import_jobs",
        db_column="template_id",
    )
    content_version: models.ForeignKey[ContentVersion | None, ContentVersion | None] = models.ForeignKey(
        "ContentVersion",
        on_delete=models.SET_NULL,
        related_name="import_jobs",
        db_column="content_version_id",
        default=None,
        null=True,
        blank=True,
    )
    options_json = models.JSONField(default=dict)
    status: models.TextField[str, str] = models.TextField(default=ImportJobStatus.queued)
    total_items: models.IntegerField[int, int] = models.IntegerField(default=0)
    processed_items: models.IntegerField[int, int] = models.IntegerField(default=0)

    class Meta:
        db_table = "import_job"


class ImportJobItem(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    job: models.ForeignKey[ImportJob, ImportJob] = models.ForeignKey(
        "ImportJob",
        on_delete=models.CASCADE,
        related_name="items",
        db_column="job_id",
    )
    source_file: models.TextField[str, str] = models.TextField()
    target_card: models.ForeignKey[Card | None, Card | None] = models.ForeignKey(
        "Card",
        on_delete=models.SET_NULL,
        related_name="+",
        db_column="target_card_id",
        default=None,
        null=True,
        blank=True,
    )
    target_card_version: models.ForeignKey[CardVersion | None, CardVersion | None] = models.ForeignKey(
        "CardVersion",
        on_delete=models.SET_NULL,
        related_name="+",
        db_column="target_card_version_id",
        default=None,
        null=True,
        blank=True,
    )
    status: models.TextField[str, str] = models.TextField(default=ImportJobStatus.queued)
    error_message: models.TextField[str | None, str | None] = models.TextField(
        default=None,
        null=True,
    )
    warning_code: models.TextField[str | None, str | None] = models.TextField(
        default=None,
        null=True,
        blank=True,
    )
    warning_message: models.TextField[str | None, str | None] = models.TextField(
        default=None,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "import_job_item"


