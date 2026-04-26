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
    id = models.TextField(default=uuid_str, primary_key=True)
    source_path = models.TextField()
    template_id = models.TextField()
    options_json = models.TextField(default="{}")
    status = models.TextField(default=ImportJobStatus.queued)
    total_items = models.IntegerField(default=0)
    processed_items = models.IntegerField(default=0)

    class Meta:
        db_table = "import_job"


class ImportJobItem(TimestampedModel):
    id = models.TextField(default=uuid_str, primary_key=True)
    job_id = models.TextField(db_index=True)
    source_file = models.TextField()
    status = models.TextField(default=ImportJobStatus.queued)
    error_message = models.TextField(default=None, null=True)

    class Meta:
        db_table = "import_job_item"


