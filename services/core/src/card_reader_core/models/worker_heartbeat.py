from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from django.db import models

from .base import TimestampedModel, now_utc, uuid_str


class WorkerActivity(StrEnum):
    idle = "idle"
    busy = "busy"
    stopped = "stopped"


class WorkerHeartbeat(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    worker_key: models.CharField[str, str] = models.CharField(max_length=80, db_index=True)
    display_name: models.CharField[str, str] = models.CharField(max_length=120)
    activity: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=[(value.value, value.value) for value in WorkerActivity],
        default=WorkerActivity.idle,
    )
    current_work_id: models.TextField[str | None, str | None] = models.TextField(
        default=None,
        null=True,
        blank=True,
    )
    started_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(default=now_utc)
    last_heartbeat_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(
        default=now_utc,
        db_index=True,
    )
    stopped_at: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "worker_heartbeat"
        ordering = ["worker_key", "-last_heartbeat_at"]
        indexes = [
            models.Index(
                fields=["worker_key", "-last_heartbeat_at"],
                name="ix_worker_heartbeat_recent",
            )
        ]
