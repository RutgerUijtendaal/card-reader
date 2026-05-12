from __future__ import annotations

from enum import StrEnum

from django.db import models

from .base import TimestampedModel, uuid_str


class ImportJobStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class ImportJob(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    source_path: models.TextField[str, str] = models.TextField()
    template_id: models.TextField[str, str] = models.TextField()
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
    status: models.TextField[str, str] = models.TextField(default=ImportJobStatus.queued)
    error_message: models.TextField[str | None, str | None] = models.TextField(
        default=None,
        null=True,
    )

    class Meta:
        db_table = "import_job_item"


